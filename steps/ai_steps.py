import json
import os
from behave import given, when, then

# Because the file is now a proper Python file, this standard import will work flawlessly!
from services.ice_api_client import WhatsAppClient
from services.llm_client import AzureAttackGenerator
from services.conversation_logger import ConversationLogger
from services.db_client import DatabaseClient
from services.self_evaluator import SelfEvaluator
# ... (Your @given, @when, @then steps remain exactly the same below this)


@given('Policy Pilot behavior rules are loaded')
def step_load_rules(context):
    config_path = os.path.join(os.getcwd(), 'config', 'behavior_instructions.json')
    with open(config_path, 'r') as f:
        context.behavior_data = json.load(f)

    context.rules = context.behavior_data['categories']
    context.mock_data = context.behavior_data['mock_data']


@given('the Policy Pilot WhatsApp number is "{phone}"')
def step_set_whatsapp_number(context, phone):
    context.phone = phone
    # Initialize the new API Client (This starts the Flask webhook listener on port 5000)
    context.whatsapp_client = WhatsAppClient(phone=context.phone)

    # Initialize Database and Logger
    context.db_client = DatabaseClient()
    context.conversation_id = context.db_client.create_conversation_record()

    # Use the unique reference from the database to name the local JSON log
    context.logger = ConversationLogger(session_id=context.db_client.unique_ref)


@given('the test category is "{category}"')
def step_set_category(context, category):
    context.category = category
    context.category_rules = context.rules.get(category, "")


@given('the test type is "{test_type}"')
def step_set_test_type(context, test_type):
    context.test_type = test_type


@given('the conversation should run for "{msg_limit}" messages')
def step_set_msg_limit(context, msg_limit):
    context.msg_limit = int(msg_limit)


@when('the attack agent starts the conversation')
def step_start_conversation(context):
    # Initialize the LLM attack generator
    attack_generator = AzureAttackGenerator(
        rules=context.category_rules,
        test_type=context.test_type,
        mock_data=context.mock_data,
        category=context.category
    )

    conversation_history = ""

    for i in range(context.msg_limit):
        print(f"\n--- Turn {i + 1} of {context.msg_limit} ---")

        # 1. Generate Attack Message
        attack_msg = attack_generator.generate_message(conversation_history)

        # 2. Send via API
        context.whatsapp_client.send_message(attack_msg)

        # 3. Log the outbound message
        context.logger.log("user", attack_msg)
        context.db_client.insert_message("user", attack_msg, context.conversation_id)
        conversation_history += f"User: {attack_msg}\n"

        # 4. Wait for Webhook Response from ICE
        # This will block until Flask receives the payload or it times out
        bot_response = context.whatsapp_client.read_response_with_timeout(timeout=120)

        if bot_response:
            print(f"Bot replied: {bot_response}")
            context.logger.log("bot", bot_response)
            context.db_client.insert_message("bot", bot_response, context.conversation_id)
            conversation_history += f"Bot: {bot_response}\n"
        else:
            print("No response from bot. Ending conversation loop early.")
            break

    # Save the full transcript in context for later evaluation
    context.full_transcript = conversation_history


@then('the conversation should terminate correctly')
def step_terminate_conversation(context):
    # If the local Flask server needs explicit shutdown, you can trigger it here.
    # However, since we started it as a daemon thread in whatsapp_client,
    # it will naturally shut down when the test run finishes.
    assert len(context.logger.messages) > 0, "No messages were sent or received."


@then('all messages should be saved in a session log')
def step_save_session_log(context):
    context.saved_file_path = context.logger.save_local_json()
    assert os.path.exists(context.saved_file_path), "Failed to save local JSON session log."


@then('all results should be stored in the database')
def step_store_evaluations(context):
    # Evaluate the conversation using the LLM judge
    attack_generator = AzureAttackGenerator(
        rules=context.category_rules,
        test_type=context.test_type,
        mock_data=context.mock_data,
        category=context.category
    )

    # Get JSON evaluation
    evaluations = attack_generator.judge_conversation(context.full_transcript)

    # Store each verdict in the database (assuming msg_id maps to conversation turns)
    # Note: You may need to adjust the message_id tracking depending on your exact DB schema
    for msg_index, eval_data in evaluations.items():
        verdict = eval_data.get("verdict", "FAIL")
        reason = eval_data.get("reason", "No reason provided")

        context.db_client.insert_evaluation(
            conv_id=context.conversation_id,
            msg_id=int(msg_index) if msg_index.isdigit() else 0,
            verdict=verdict,
            reason=reason
        )

    print("Database logging and evaluation complete.")
