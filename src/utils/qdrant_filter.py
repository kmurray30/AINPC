import ast
import re
from typing import Union, List
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny


class QdrantFilter:
    """
    A class to parse human-readable filter expressions for Qdrant tag filtering.
    
    Supports expressions like:
    - "'social'"
    - "'social' and 'happy'"
    - "'sad' or 'angry'"
    - "'social' and ('sad' or 'angry')"
    - "not 'dangerous'"
    - "('social' or 'work') and not ('sad' or 'angry')"
    
    All tag matching uses ANY semantics (entity has the tag among others).
    """
    
    def __init__(self, expression: str):
        self.expression = expression.strip()
        if not self.expression:
            raise ValueError("Filter expression cannot be empty")
        
        self.filter = self._parse_expression()
    
    def _parse_expression(self) -> Filter:
        """Parse the expression string into a Qdrant Filter object"""
        try:
            # Normalize the expression for parsing
            normalized = self._normalize_expression(self.expression)
            
            # Parse as Python AST
            tree = ast.parse(normalized, mode='eval')
            
            # Convert AST to Qdrant filter
            return self._ast_to_filter(tree.body)
            
        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Invalid filter expression '{self.expression}': {e}")
    
    def _normalize_expression(self, expr: str) -> str:
        """Normalize the expression for AST parsing"""
        # Replace quoted strings with Python-compatible identifiers first
        # This allows us to parse tag names with spaces
        self._tag_map = {}
        self._tag_counter = 0
        
        def replace_quoted(match):
            tag_name = match.group(1)
            placeholder = f"tag_{self._tag_counter}"
            self._tag_map[placeholder] = tag_name
            self._tag_counter += 1
            return placeholder
        
        # Match single-quoted strings (supporting spaces and special chars, but not escaped quotes for now)
        expr = re.sub(r"'([^'\\]+)'", replace_quoted, expr)
        
        # Make operators case-insensitive by converting to lowercase
        # Use word boundaries to avoid matching parts of identifiers
        expr = re.sub(r'\b(AND|And)\b', ' and ', expr)
        expr = re.sub(r'\b(OR|Or)\b', ' or ', expr)  
        expr = re.sub(r'\b(NOT|Not)\b', ' not ', expr)
        
        # Also handle cases where operators are adjacent to quotes/identifiers without spaces
        expr = re.sub(r'(\w|\')\s*and\s*(\w|\')', r'\1 and \2', expr)
        expr = re.sub(r'(\w|\')\s*or\s*(\w|\')', r'\1 or \2', expr)
        expr = re.sub(r'(\w|\')\s*not\s*(\w|\')', r'\1 not \2', expr)
        
        # Clean up extra whitespace and strip leading/trailing spaces
        expr = re.sub(r'\s+', ' ', expr).strip()
        
        return expr
    
    def _ast_to_filter(self, node: ast.AST) -> Filter:
        """Convert AST node to Qdrant Filter"""
        if isinstance(node, ast.Name):
            # Single tag reference
            tag_name = self._tag_map.get(node.id, node.id)
            return Filter(must=[FieldCondition(key="tags", match=MatchValue(value=tag_name))])
            
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                # AND operation - all conditions must be true
                conditions = []
                for value in node.values:
                    sub_filter = self._ast_to_filter(value)
                    conditions.extend(sub_filter.must or [])
                return Filter(must=conditions)
                
            elif isinstance(node.op, ast.Or):
                # OR operation - at least one condition must be true
                conditions = []
                for value in node.values:
                    sub_filter = self._ast_to_filter(value)
                    conditions.extend(sub_filter.must or [])
                return Filter(should=conditions)
                
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            # NOT operation
            sub_filter = self._ast_to_filter(node.operand)
            
            # Handle different sub-filter types
            must_not_conditions = []
            if sub_filter.must:
                must_not_conditions.extend(sub_filter.must)
            elif sub_filter.should:
                must_not_conditions.extend(sub_filter.should)
            elif sub_filter.must_not:
                # Double negation - convert must_not back to must
                return Filter(must=sub_filter.must_not)
            
            return Filter(must_not=must_not_conditions)
            
        else:
            raise ValueError(f"Unsupported expression type: {type(node)}")
    
    def to_qdrant_filter(self) -> Filter:
        """Get the Qdrant Filter object"""
        return self.filter


def parse_filter_string(filter_expr: Union[str, Filter, None]) -> Union[Filter, None]:
    """
    Utility function to convert a filter expression to a Qdrant Filter.
    
    Args:
        filter_expr: Can be:
            - None: No filtering
            - str: Parse as QdrantFilter expression
            - Filter: Pass through as-is
    
    Returns:
        Filter object or None
    """
    if filter_expr is None or filter_expr == "":
        return None
    elif isinstance(filter_expr, str):
        return QdrantFilter(filter_expr).to_qdrant_filter()
    elif isinstance(filter_expr, Filter):
        return filter_expr
    else:
        raise ValueError(f"Invalid filter type: {type(filter_expr)}. Expected str, Filter, or None.")
