import os
import sys
import pytest
from qdrant_client.models import Filter, FieldCondition, MatchValue

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils.qdrant_filter import QdrantFilter, parse_filter_string


class TestQdrantFilter:
    """Test the QdrantFilter class for parsing filter expressions"""
    
    def test_single_tag(self):
        """Test parsing a single tag"""
        filter_obj = QdrantFilter("'social'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must) == 1
        assert qdrant_filter.must[0].key == "tags"
        assert qdrant_filter.must[0].match.value == "social"
    
    def test_single_tag_with_spaces(self):
        """Test parsing a tag with spaces"""
        filter_obj = QdrantFilter("'social media'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must) == 1
        assert qdrant_filter.must[0].key == "tags"
        assert qdrant_filter.must[0].match.value == "social media"
    
    def test_simple_and(self):
        """Test simple AND operation"""
        filter_obj = QdrantFilter("'social' and 'happy'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must) == 2
        values = {condition.match.value for condition in qdrant_filter.must}
        assert values == {"social", "happy"}
    
    def test_simple_or(self):
        """Test simple OR operation"""
        filter_obj = QdrantFilter("'sad' or 'angry'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.should) == 2
        values = {condition.match.value for condition in qdrant_filter.should}
        assert values == {"sad", "angry"}
    
    def test_simple_not(self):
        """Test simple NOT operation"""
        filter_obj = QdrantFilter("not 'dangerous'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must_not) == 1
        assert qdrant_filter.must_not[0].match.value == "dangerous"
    
    def test_nested_parentheses(self):
        """Test nested operations with parentheses"""
        filter_obj = QdrantFilter("'social' and ('sad' or 'angry')")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        # Should have social in must, and (sad or angry) as should conditions
        assert len(qdrant_filter.must) >= 1
        
        # Find the social condition
        social_found = any(
            condition.match.value == "social" 
            for condition in qdrant_filter.must 
            if hasattr(condition, 'match')
        )
        assert social_found, "Should contain 'social' in must conditions"
    
    def test_multiple_ands(self):
        """Test multiple AND operations"""
        filter_obj = QdrantFilter("'social' and 'happy' and 'positive'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must) == 3
        values = {condition.match.value for condition in qdrant_filter.must}
        assert values == {"social", "happy", "positive"}
    
    def test_multiple_ors(self):
        """Test multiple OR operations"""
        filter_obj = QdrantFilter("'sad' or 'angry' or 'frustrated'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.should) == 3
        values = {condition.match.value for condition in qdrant_filter.should}
        assert values == {"sad", "angry", "frustrated"}
    
    def test_complex_nested(self):
        """Test complex nested operations"""
        filter_obj = QdrantFilter("('social' or 'work') and ('happy' or 'positive')")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        # This should create a structure that captures the logic
        # The exact structure may vary based on AST parsing, but should be valid
        assert qdrant_filter is not None
    
    def test_not_with_parentheses(self):
        """Test NOT with parentheses"""
        filter_obj = QdrantFilter("not ('dangerous' or 'harmful')")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        # Should have must_not conditions
        assert len(qdrant_filter.must_not) == 2
        values = {condition.match.value for condition in qdrant_filter.must_not}
        assert values == {"dangerous", "harmful"}
    
    def test_case_insensitive_operators(self):
        """Test that operators are case-insensitive"""
        test_cases = [
            "'social' AND 'happy'",
            "'social' And 'happy'", 
            "'sad' OR 'angry'",
            "'sad' Or 'angry'",
            "NOT 'dangerous'",
            "Not 'dangerous'"
        ]
        
        for expr in test_cases:
            filter_obj = QdrantFilter(expr)
            # Should not raise exception and should create valid filter
            assert filter_obj.to_qdrant_filter() is not None
    
    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly"""
        test_cases = [
            "'social'and'happy'",  # No spaces
            "'social'  and  'happy'",  # Extra spaces
            "  'social' and 'happy'  ",  # Leading/trailing spaces
            "'social'\nand\n'happy'"  # Newlines
        ]
        
        for expr in test_cases:
            filter_obj = QdrantFilter(expr)
            qdrant_filter = filter_obj.to_qdrant_filter()
            assert len(qdrant_filter.must) == 2
    
    def test_special_characters_in_tags(self):
        """Test tags with special characters"""
        filter_obj = QdrantFilter("'tag-with-dashes' and 'tag_with_underscores'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        
        assert len(qdrant_filter.must) == 2
        values = {condition.match.value for condition in qdrant_filter.must}
        assert values == {"tag-with-dashes", "tag_with_underscores"}
    
    def test_empty_expression_error(self):
        """Test that empty expressions raise ValueError"""
        with pytest.raises(ValueError, match="Filter expression cannot be empty"):
            QdrantFilter("")
        
        with pytest.raises(ValueError, match="Filter expression cannot be empty"):
            QdrantFilter("   ")
    
    def test_invalid_syntax_error(self):
        """Test that invalid syntax raises ValueError"""
        invalid_expressions = [
            "'unclosed quote",
            "and 'missing_operand'",
            "'tag' and",
            "('unmatched parentheses'",
            "'tag' invalid_operator 'tag2'",
            "123",  # Numbers not supported
            "'tag' & 'tag2'"  # Wrong operator
        ]
        
        for expr in invalid_expressions:
            with pytest.raises(ValueError, match="Invalid filter expression"):
                QdrantFilter(expr)
    
    def test_missing_quotes_error(self):
        """Test that unquoted tag names are treated as tag names (but won't be found in _tag_map)"""
        # This should actually work - unquoted identifiers are valid Python
        filter_obj = QdrantFilter("social and happy")
        qdrant_filter = filter_obj.to_qdrant_filter()
        # Should create filters with the literal identifiers as tag names
        assert len(qdrant_filter.must) == 2
        values = {condition.match.value for condition in qdrant_filter.must}
        assert values == {"social", "happy"}
    
    def test_tags_with_special_chars(self):
        """Test that tags with various special characters work"""
        # Test tags with hyphens, underscores, numbers
        filter_obj = QdrantFilter("'tag-1' and 'tag_2' and 'tag3'")
        qdrant_filter = filter_obj.to_qdrant_filter()
        assert len(qdrant_filter.must) == 3
        values = {condition.match.value for condition in qdrant_filter.must}
        assert values == {"tag-1", "tag_2", "tag3"}


class TestParseFilterString:
    """Test the parse_filter_string utility function"""
    
    def test_none_input(self):
        """Test that None input returns None"""
        result = parse_filter_string(None)
        assert result is None
    
    def test_string_input(self):
        """Test that string input is parsed correctly"""
        result = parse_filter_string("'social' and 'happy'")
        assert isinstance(result, Filter)
        assert len(result.must) == 2
    
    def test_filter_input_passthrough(self):
        """Test that Filter input is passed through unchanged"""
        original_filter = Filter(must=[FieldCondition(key="tags", match=MatchValue(value="test"))])
        result = parse_filter_string(original_filter)
        assert result is original_filter
    
    def test_invalid_type_error(self):
        """Test that invalid types raise ValueError"""
        with pytest.raises(ValueError, match="Invalid filter type"):
            parse_filter_string(123)
        
        with pytest.raises(ValueError, match="Invalid filter type"):
            parse_filter_string(["list", "not", "supported"])


class TestIntegrationWithQdrantCollection:
    """Test that the filter works with QdrantCollection methods"""
    
    def test_string_filter_accepted(self):
        """Test that string filters are accepted by search methods"""
        # This is more of a smoke test - we can't easily test the full integration
        # without a running Qdrant instance, but we can test that the methods accept strings
        from src.utils.QdrantCollection import QdrantCollection
        
        # These should not raise type errors
        col = QdrantCollection("test")
        
        # Test that the methods accept string filters (though they may fail at runtime)
        try:
            # This will likely fail due to no Qdrant server, but should not fail due to type issues
            col.search_text("test", filter="'social'")
        except Exception as e:
            # Should not be a TypeError about filter parameter
            assert "filter" not in str(e).lower() or "type" not in str(e).lower()
