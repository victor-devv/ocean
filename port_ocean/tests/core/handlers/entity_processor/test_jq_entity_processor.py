from typing import Any
from unittest.mock import AsyncMock, Mock
import pytest

from port_ocean.context.ocean import PortOceanContext
from port_ocean.core.handlers.entity_processor.jq_entity_processor import (
    JQEntityProcessor,
)
from port_ocean.core.ocean_types import CalculationResult
from port_ocean.exceptions.core import EntityProcessorException


@pytest.mark.asyncio
class TestJQEntityProcessor:

    @pytest.fixture
    def mocked_processor(self, monkeypatch: Any) -> JQEntityProcessor:
        mock_context = AsyncMock()
        monkeypatch.setattr(PortOceanContext, "app", mock_context)
        return JQEntityProcessor(mock_context)

    async def test_compile(self, mocked_processor: JQEntityProcessor) -> None:
        pattern = ".foo"
        compiled = mocked_processor._compile(pattern)
        assert compiled is not None

    async def test_search(self, mocked_processor: JQEntityProcessor) -> None:
        data = {"foo": "bar"}
        pattern = ".foo"
        result = await mocked_processor._search(data, pattern)
        assert result == "bar"

    async def test_search_as_bool(self, mocked_processor: JQEntityProcessor) -> None:
        data = {"foo": True}
        pattern = ".foo"
        result = await mocked_processor._search_as_bool(data, pattern)
        assert result is True

    async def test_search_as_object(self, mocked_processor: JQEntityProcessor) -> None:
        data = {"foo": {"bar": "baz"}}
        obj = {"foo": ".foo.bar"}
        result = await mocked_processor._search_as_object(data, obj)
        assert result == {"foo": "baz"}

    async def test_get_mapped_entity(self, mocked_processor: JQEntityProcessor) -> None:
        data = {"foo": "bar"}
        raw_entity_mappings = {"foo": ".foo"}
        selector_query = '.foo == "bar"'
        result = await mocked_processor._get_mapped_entity(
            data, raw_entity_mappings, selector_query
        )
        assert result.entity == {"foo": "bar"}
        assert result.did_entity_pass_selector is True

    async def test_calculate_entity(self, mocked_processor: JQEntityProcessor) -> None:
        data = {"foo": "bar"}
        raw_entity_mappings = {"foo": ".foo"}
        selector_query = '.foo == "bar"'
        result, errors = await mocked_processor._calculate_entity(
            data, raw_entity_mappings, None, selector_query
        )
        assert len(result) == 1
        assert result[0].entity == {"foo": "bar"}
        assert result[0].did_entity_pass_selector is True
        assert not errors

    async def test_parse_items(self, mocked_processor: JQEntityProcessor) -> None:
        mapping = Mock()
        mapping.port.entity.mappings.dict.return_value = {
            "identifier": ".foo",
            "blueprint": ".foo",
            "properties": {"foo": ".foo"},
        }
        mapping.port.items_to_parse = None
        mapping.selector.query = '.foo == "bar"'
        raw_results = [{"foo": "bar"}]
        result = await mocked_processor._parse_items(mapping, raw_results)
        assert isinstance(result, CalculationResult)
        assert len(result.entity_selector_diff.passed) == 1
        assert result.entity_selector_diff.passed[0].properties.get("foo") == "bar"
        assert not result.errors

    async def test_in_operator(self, mocked_processor: JQEntityProcessor) -> None:
        data = {
            "key": "GetPort_SelfService",
            "name": "GetPort SelfService",
            "desc": "Test",
            "qualifier": "VW",
            "visibility": "public",
            "selectionMode": "NONE",
            "subViews": [
                {
                    "key": "GetPort_SelfService_Second",
                    "name": "GetPort SelfService Second",
                    "qualifier": "SVW",
                    "selectionMode": "NONE",
                    "subViews": [
                        {
                            "key": "GetPort_SelfService_Third",
                            "name": "GetPort SelfService Third",
                            "qualifier": "SVW",
                            "selectionMode": "NONE",
                            "subViews": [],
                            "referencedBy": [],
                        },
                        {
                            "key": "Port_Test",
                            "name": "Port Test",
                            "qualifier": "SVW",
                            "selectionMode": "NONE",
                            "subViews": [],
                            "referencedBy": [],
                        },
                    ],
                    "referencedBy": [],
                },
                {
                    "key": "Python",
                    "name": "Python",
                    "qualifier": "SVW",
                    "selectionMode": "NONE",
                    "subViews": [
                        {
                            "key": "Time",
                            "name": "Time",
                            "qualifier": "SVW",
                            "selectionMode": "NONE",
                            "subViews": [
                                {
                                    "key": "port_*****",
                                    "name": "port-*****",
                                    "qualifier": "SVW",
                                    "selectionMode": "NONE",
                                    "subViews": [
                                        {
                                            "key": "port_*****:REferenced",
                                            "name": "REferenced",
                                            "qualifier": "VW",
                                            "visibility": "public",
                                            "originalKey": "REferenced",
                                        }
                                    ],
                                    "referencedBy": [],
                                }
                            ],
                            "referencedBy": [],
                        }
                    ],
                    "referencedBy": [],
                },
                {
                    "key": "GetPort_SelfService:Authentication_Application",
                    "name": "Authentication Application",
                    "desc": "For auth services",
                    "qualifier": "APP",
                    "visibility": "private",
                    "selectedBranches": ["main"],
                    "originalKey": "Authentication_Application",
                },
            ],
            "referencedBy": [],
        }
        pattern = '.subViews | map(select((.qualifier | IN("VW", "SVW"))) | .key)'
        result = await mocked_processor._search(data, pattern)
        assert result == ["GetPort_SelfService_Second", "Python"]

    async def test_failure_of_jq_expression(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        data = {"foo": "bar"}
        pattern = ".foo."
        result = await mocked_processor._search(data, pattern)
        assert result is None

    async def test_search_as_object_failure(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        data = {"foo": {"bar": "baz"}}
        obj = {"foo": ".foo.bar."}
        result = await mocked_processor._search_as_object(data, obj)
        assert result == {"foo": None}

    async def test_double_quotes_in_jq_expression(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        data = {"foo": "bar"}
        pattern = '"shalom"'
        result = await mocked_processor._search(data, pattern)
        assert result == "shalom"

    async def test_search_as_bool_failure(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        data = {"foo": "bar"}
        pattern = ".foo"
        with pytest.raises(
            EntityProcessorException,
            match="Expected boolean value, got <class 'str'> instead",
        ):
            await mocked_processor._search_as_bool(data, pattern)

    @pytest.mark.timeout(3)
    async def test_search_performance_10000(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        """
        This test is to check the performance of the search method when called 10000 times.
        """
        data = {"foo": "bar"}
        pattern = ".foo"
        for _ in range(10000):
            result = await mocked_processor._search(data, pattern)
            assert result == "bar"

    @pytest.mark.timeout(15)
    async def test_parse_items_performance_10000(
        self, mocked_processor: JQEntityProcessor
    ) -> None:
        """
        This test is to check the performance of the parse_items method when called 10000 times.
        """
        mapping = Mock()
        mapping.port.entity.mappings.dict.return_value = {
            "identifier": ".foo",
            "blueprint": ".foo",
            "properties": {"foo": ".foo"},
        }
        mapping.port.items_to_parse = None
        mapping.selector.query = '.foo == "bar"'
        raw_results = [{"foo": "bar"}]
        for _ in range(10000):
            result = await mocked_processor._parse_items(mapping, raw_results)
            assert isinstance(result, CalculationResult)
            assert len(result.entity_selector_diff.passed) == 1
            assert result.entity_selector_diff.passed[0].properties.get("foo") == "bar"
            assert not result.errors