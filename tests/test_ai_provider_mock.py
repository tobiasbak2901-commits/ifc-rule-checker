from ai.models import AIContext, ViewerState
from ai.providers.mock import MockProvider


def test_mock_provider_rephrase_works_without_network():
    provider = MockProvider()
    context = AIContext(
        project_id="demo",
        project_root=".",
        viewer_state=ViewerState(active_mode="Analyze"),
    )
    out = provider.rephrase("Kort forklaring", context, ["RULE:SEARCH_SET_CLASH"])
    assert out.startswith("Ponker siger:")
