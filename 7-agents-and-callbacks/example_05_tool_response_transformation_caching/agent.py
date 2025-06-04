import copy
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from google.adk.agents import Agent as LlmAgent
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService, Session
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

MOCK_RATES = {
    ("USD", "EUR"): 0.92,
    ("EUR", "USD"): 1.08,
    ("GBP", "USD"): 1.27,
    ("USD", "GBP"): 0.79,
    ("USD", "JPY"): 150.50,
    ("JPY", "USD"): 0.0066,
}
CACHE_EXPIRY_SECONDS = 10

session_service = InMemorySessionService()
app_name, user_id, session_id = "state_app_manual", "user2", "session2"
session = session_service.create_session(
    app_name=app_name,
    user_id=user_id,
    session_id=session_id,
    state={"user:login_count": 0, "task_status": "idle"},
)
print(f"Initial state: {session.state}")


def convert_currency_tool(
    amount: float, from_currency: str, to_currency: str
) -> Dict[str, Any]:
    from_currency_upper = str(from_currency).upper().strip()
    to_currency_upper = str(to_currency).upper().strip()
    try:
        float_amount = float(amount)
    except ValueError:
        return {"error": "Invalid amount provided. Amount must be a number."}

    print(
        f"\n[TOOL EXECUTED] convert_currency_tool for {float_amount} {from_currency_upper} to {to_currency_upper}"
    )

    rate = MOCK_RATES.get((from_currency_upper, to_currency_upper))
    if rate:
        converted_amount = float_amount * rate
        return {
            "from_currency": from_currency_upper,
            "to_currency": to_currency_upper,
            "original_amount": float_amount,
            "converted_amount": converted_amount,
            "rate_used": rate,
        }
    else:
        return {
            "error": f"Conversion rate for {from_currency_upper} to {to_currency_upper} not available in mock data."
        }


def _generate_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
    """Helper function to generate a consistent cache key."""
    try:
        amount_val = args.get("amount")
        if amount_val is None:
            amount_str = "0.00"
        elif isinstance(amount_val, (int, float)):
            amount_str = f"{float(amount_val):.2f}"
        else:
            try:
                amount_str = f"{float(str(amount_val)):.2f}"
            except ValueError:
                amount_str = (
                    str(amount_val).lower().strip()
                    if str(amount_val).strip()
                    else "invalid_amount_str"
                )
    except Exception:
        amount_str = "amount_key_gen_error"

    from_c_str = str(args.get("from_currency", "")).upper().strip()
    to_c_str = str(args.get("to_currency", "")).upper().strip()

    key = f"{tool_name}_{amount_str}_{from_c_str}_{to_c_str}"
    return key


async def before_tool_callback_cache(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict[str, Any]]:
    tool_name = tool.name
    # get the current session instance
    session_instance = session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    callback_return_value: Dict[str, Any] = {}
    state_delta_for_tool_cache: Optional[Dict[str, Any]] = None

    if tool_name == "convert_currency_tool":
        cache_key = _generate_cache_key(tool_name, args)

        # Read current cache state (read-only access is fine)
        current_tool_cache_state = session_instance.state.get("app_cache", {})
        cached_entry = current_tool_cache_state.get(cache_key)

        if cached_entry:
            timestamp_str, cached_result_data = cached_entry
            try:
                cached_timestamp = datetime.fromisoformat(timestamp_str)
                current_time = datetime.now(timezone.utc)
                age_seconds = (current_time - cached_timestamp).total_seconds()

                print(
                    f"[CACHE DEBUG] Found entry for {cache_key}. Age: {age_seconds:.2f}s. Expiry: {CACHE_EXPIRY_SECONDS}s."
                )

                if age_seconds < CACHE_EXPIRY_SECONDS:
                    print(
                        f"[CACHE DEBUG] Using FRESH CACHED result for {cache_key}: {cached_result_data}"
                    )
                    # ADK specific way to return cached result and skip tool
                    callback_return_value["cached_result"] = copy.deepcopy(
                        cached_result_data
                    )
                    return copy.deepcopy(cached_result_data)
                    # This is the standard way to make before_tool_callback
                    # return a cached value

                else:  # Cache expired
                    print(f"[CACHE DEBUG] Cache EXPIRED for {cache_key}.")
                    # Prepare to delete the expired entry from our copy of the cache
                    new_tool_cache_state = current_tool_cache_state.copy()
                    if cache_key in new_tool_cache_state:
                        del new_tool_cache_state[cache_key]
                        print(
                            f"[CACHE DEBUG] Prepared deletion of expired entry for {cache_key}."
                        )
                    state_delta_for_tool_cache = new_tool_cache_state
                    print(
                        f"[CACHE DEBUG] Proposed cache state after deletion: {state_delta_for_tool_cache}"
                    )
                    # Proceed to actual tool call, but signal state change
            except ValueError:
                print(
                    f"[CACHE DEBUG] Invalid timestamp format in cache for {cache_key}. Treating as miss."
                )
                # Optionally prepare to delete the malformed entry
                new_tool_cache_state = current_tool_cache_state.copy()
                if cache_key in new_tool_cache_state:
                    del new_tool_cache_state[cache_key]
                    print(
                        f"[CACHE DEBUG] Prepared deletion of malformed entry for {cache_key}."
                    )
                state_delta_for_tool_cache = new_tool_cache_state
                # Proceed to actual tool call, signal state change
        else:
            print(f"[CACHE DEBUG] Cache MISS for key: {cache_key}.")
            # Proceed to actual tool call, no state change needed here from cache miss

    # this is where we actually change the state_delta for the tool call
    if state_delta_for_tool_cache is not None:
        # If there are changes to tool_cache, add them to the state_delta
        # to be returned by this callback.
        # The agent framework would then merge this into the overall state_delta for the event.
        await update_tool_context_with_cache(
            tool_context=tool_context, state_changes=state_delta_for_tool_cache
        )
        print(
            f"[BEFORE TOOL] Updated tool context with cache state delta: {state_delta_for_tool_cache}"
        )

    # If callback_return_value is empty, it means proceed with tool call without overriding anything
    # and without any new state_delta from this callback's specific logic.
    # Returning None means proceed with the tool.
    return callback_return_value if callback_return_value else None


async def after_tool_callback_format_and_cache(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    tool_name = tool.name
    print(
        f"\n[AFTER TOOL] Original tool response for '{tool_name}' with args {args}: {tool_response}"
    )
    session_instance = session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    # This callback always returns a dictionary that becomes the new tool_response
    # for the LLM. If it needs to update the cache, it includes the delta.
    modified_tool_output: Dict[str, Any] = {}
    state_delta_for_tool_cache: Optional[Dict[str, Any]] = None

    if tool_name == "convert_currency_tool":
        modified_tool_output["raw_details"] = copy.deepcopy(tool_response)

        if "converted_amount" in tool_response and "error" not in tool_response:
            cache_key = _generate_cache_key(tool_name, args)

            # Read current cache state and prepare to update it
            current_tool_cache_state = session_instance.state.get("app_cache", {})
            new_tool_cache_state = current_tool_cache_state.copy()
            new_tool_cache_state[cache_key] = (
                datetime.now(timezone.utc).isoformat(),
                copy.deepcopy(tool_response),  # Cache the original tool_response
            )
            state_delta_for_tool_cache = new_tool_cache_state
            print(
                f"[CACHE DEBUG] Prepared update/storage for {cache_key}. Proposed cache state: {state_delta_for_tool_cache}"
            )

            formatted_result_string = (
                f"{tool_response['original_amount']:.2f} {tool_response['from_currency']} is "
                f"approximately {tool_response['converted_amount']:.2f} {tool_response['to_currency']} "
                f"(Rate: {tool_response.get('rate_used', 'N/A')})."
            )
            modified_tool_output["result_summary"] = formatted_result_string

        elif "error" in tool_response:
            modified_tool_output["result_summary"] = (
                f"I encountered an issue during conversion: {tool_response['error']}"
            )
            # No caching if there's an error from the tool

            print(
                f"[AFTER TOOL] Formatted result/error for LLM: {modified_tool_output}"
            )

    if state_delta_for_tool_cache is not None:
        # Merge the state_delta into the dictionary to be returned
        await update_tool_context_with_cache(
            tool_context=tool_context, state_changes=state_delta_for_tool_cache
        )
        print(
            f"[AFTER TOOL] Updated tool context with cache state delta: {state_delta_for_tool_cache}"
        )

    if not modified_tool_output:  # Should not happen if tool_name matched
        return tool_response

    return modified_tool_output


async def update_tool_context_with_cache(
    tool_context: ToolContext, state_changes: Dict[str, Any]
) -> None:
    """Utility function to update the tool context's state with a cache delta."""
    session_instance = session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    actions_with_update = EventActions(state_delta={"app_cache": state_changes})
    # timestamp should be a number
    system_event = Event(
        invocation_id=tool_context.invocation_id,
        author="currency_converter_agent",  # Or 'agent', 'tool' etc.
        actions=actions_with_update,
        timestamp=time.time(),
    )
    # --- Append the Event (This updates the state) ---
    session_service.append_event(session_instance, system_event)
    print(
        "[Tool Call Updating Cache]: `append_event` called with explicit state delta."
    )


currency_converter_agent = LlmAgent(
    name="currency_converter_agent",
    description="Converts currencies using mock rates, demonstrates caching and response formatting.",
    tools=[convert_currency_tool],
    model="gemini-2.0-flash",
    instruction="You are a currency converter. When asked to convert currency, use the convert_currency_tool. Based on the tool's output (look for 'result_summary' or 'error_message' in the tool's returned dictionary), provide a clear and concise answer to the user.",
    before_tool_callback=before_tool_callback_cache,
    after_tool_callback=after_tool_callback_format_and_cache,
)

root_agent = currency_converter_agent
