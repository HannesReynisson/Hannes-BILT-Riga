import os
import secrets
import string

import pytest
from gql import gql
from speckle_automate import (
    AutomationContext,
    AutomationRunData,
    AutomationStatus,
    run_function,
)
from specklepy.api.client import SpeckleClient

from main import FunctionInputs, automate_function


def crypto_random_string(length: int) -> str:
    """Generate a semi crypto random string of a given length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def register_new_automation(
    project_id: str,
    model_id: str,
    speckle_client: SpeckleClient,
    automation_id: str,
    automation_name: str,
    automation_revision_id: str,
):
    """Register a new automation in the speckle server."""
    query = gql(
        """
        mutation CreateAutomation(
            $projectId: String! 
            $modelId: String! 
            $automationName: String!
            $automationId: String! 
            $automationRevisionId: String!
        ) {
                automationMutations {
                    create(
                        input: {
                            projectId: $projectId
                            modelId: $modelId
                            automationName: $automationName 
                            automationId: $automationId
                            automationRevisionId: $automationRevisionId
                        }
                    )
                }
            }
        """
    )
    params = {
        "projectId": project_id,
        "modelId": model_id,
        "automationName": automation_name,
        "automationId": automation_id,
        "automationRevisionId": automation_revision_id,
    }
    speckle_client.httpclient.execute(query, params)


@pytest.fixture()
def speckle_token() -> str:
    """Provide a speckle token for the test suite."""
    env_var = "SPECKLE_TOKEN"
    token = os.getenv(env_var)
    if not token:
        raise ValueError(f"Cannot run tests without a {env_var} environment variable")
    return token


@pytest.fixture()
def speckle_server_url() -> str:
    """Provide a speckle server url for the test suite, default to localhost."""
    return os.getenv("SPECKLE_SERVER_URL", "http://127.0.0.1:3000")


@pytest.fixture()
def test_client(speckle_server_url: str, speckle_token: str) -> SpeckleClient:
    """Initialize a SpeckleClient for testing."""
    test_client = SpeckleClient(
        speckle_server_url, speckle_server_url.startswith("https")
    )
    test_client.authenticate_with_token(speckle_token)
    return test_client


@pytest.fixture()
# fixture to mock the AutomationRunData that would be generated by a full Automation Run
def fake_automation_run_data(request, test_client: SpeckleClient) -> AutomationRunData:
    server_url = request.config.SPECKLE_SERVER_URL
    project_id = "ce0f229748"
    model_id = "634a39fa45"

    function_name = "BILT Riga Workshop"

    automation_id = crypto_random_string(10)
    automation_name = "Local Test"
    automation_revision_id = crypto_random_string(10)

    register_new_automation(
        project_id,
        model_id,
        test_client,
        automation_id,
        automation_name,
        automation_revision_id,
    )

    fake_run_data = AutomationRunData(
        project_id=project_id,
        model_id=model_id,
        branch_name="basic",
        version_id="df0f86a3fd",
        speckle_server_url=server_url,
        # These ids would be available with a valid registered Automation definition.
        automation_id=automation_id,
        automation_revision_id=automation_revision_id,
        automation_run_id=crypto_random_string(12),
        # These ids would be available with a valid registered Function definition. Can also be faked.
        function_id="12345",
        function_name=function_name,
        function_logo=None,
    )

    return fake_run_data


def test_function_run(fake_automation_run_data: AutomationRunData, speckle_token: str):
    """Run an integration test for the automate function."""
    context = AutomationContext.initialize(fake_automation_run_data, speckle_token)

    automate_sdk = run_function(
        context,
        automate_function,
        FunctionInputs(commentPhrase="Test Locally"),
        # FunctionInputs(
        #     tolerance=0.1, tolerance_unit="mm", static_model_name="simple beams"
        # ),
    )

    assert automate_sdk.run_status == AutomationStatus.SUCCEEDED
