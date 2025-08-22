"""GraphQL-specific analysis and introspection."""

import json
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .models import CapturedRequest, CapturedResponse
from .storage import StorageBackend


@dataclass
class GraphQLOperation:
    type: str  # query, mutation, subscription
    name: Optional[str]
    query: str
    variables: Optional[Dict[str, Any]]
    fields: List[str]
    fragments: List[str] = field(default_factory=list)


@dataclass
class GraphQLSchema:
    types: Dict[str, Dict[str, Any]]
    queries: Dict[str, Dict[str, Any]]
    mutations: Dict[str, Dict[str, Any]]
    subscriptions: Dict[str, Dict[str, Any]]
    directives: List[str]
    scalar_types: Set[str]


class GraphQLAnalyzer:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.introspection_query = """
        query IntrospectionQuery {
          __schema {
            queryType { name }
            mutationType { name }
            subscriptionType { name }
            types {
              ...FullType
            }
            directives {
              name
              description
              locations
              args {
                ...InputValue
              }
            }
          }
        }

        fragment FullType on __Type {
          kind
          name
          description
          fields(includeDeprecated: true) {
            name
            description
            args {
              ...InputValue
            }
            type {
              ...TypeRef
            }
            isDeprecated
            deprecationReason
          }
          inputFields {
            ...InputValue
          }
          interfaces {
            ...TypeRef
          }
          enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
          }
          possibleTypes {
            ...TypeRef
          }
        }

        fragment InputValue on __InputValue {
          name
          description
          type { ...TypeRef }
          defaultValue
        }

        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
    
    def analyze_graphql_traffic(self, host: str) -> Dict[str, Any]:
        """Analyze captured GraphQL traffic for a host."""
        requests = self.storage.get_requests_by_host(host)
        
        graphql_requests = []
        operations = defaultdict(list)
        
        for request in requests:
            if self._is_graphql_request(request):
                operation = self._parse_graphql_request(request)
                if operation:
                    graphql_requests.append(request)
                    operations[operation.type].append(operation)
        
        # Analyze patterns
        schema = self._infer_schema_from_operations(operations)
        
        return {
            "host": host,
            "total_operations": len(graphql_requests),
            "queries": len(operations["query"]),
            "mutations": len(operations["mutation"]),
            "subscriptions": len(operations["subscription"]),
            "unique_operations": self._get_unique_operations(operations),
            "inferred_schema": schema,
            "common_variables": self._analyze_common_variables(operations),
            "error_patterns": self._analyze_error_patterns(graphql_requests)
        }
    
    def _is_graphql_request(self, request: CapturedRequest) -> bool:
        """Check if a request is a GraphQL request."""
        # Check URL patterns
        if "/graphql" in request.path.lower() or "/gql" in request.path.lower():
            return True
        
        # Check content type
        if request.content_type and "json" in request.content_type.value:
            # Check body for GraphQL patterns
            if request.body_decoded:
                try:
                    data = json.loads(request.body_decoded)
                    return "query" in data or "mutation" in data or "subscription" in data
                except:
                    pass
        
        return False
    
    def _parse_graphql_request(self, request: CapturedRequest) -> Optional[GraphQLOperation]:
        """Parse a GraphQL request to extract operation details."""
        if not request.body_decoded:
            return None
        
        try:
            data = json.loads(request.body_decoded)
            
            # Get the query string
            query = data.get("query", "")
            if not query:
                return None
            
            # Determine operation type and name
            op_type, op_name = self._extract_operation_info(query)
            
            # Extract fields being requested
            fields = self._extract_fields(query)
            
            # Extract fragments
            fragments = self._extract_fragments(query)
            
            return GraphQLOperation(
                type=op_type,
                name=op_name,
                query=query,
                variables=data.get("variables"),
                fields=fields,
                fragments=fragments
            )
        except:
            return None
    
    def _extract_operation_info(self, query: str) -> tuple[str, Optional[str]]:
        """Extract operation type and name from query."""
        # Remove comments
        query = re.sub(r'#.*$', '', query, flags=re.MULTILINE)
        
        # Match operation declaration
        match = re.match(r'^\s*(query|mutation|subscription)\s*(\w+)?', query, re.IGNORECASE)
        if match:
            return match.group(1).lower(), match.group(2)
        
        # Default to query if no explicit operation
        if '{' in query:
            return "query", None
        
        return "query", None
    
    def _extract_fields(self, query: str) -> List[str]:
        """Extract field names from GraphQL query."""
        fields = []
        
        # Simple regex to find field names (not perfect but good enough)
        # Matches word characters followed by optional arguments and selection set
        pattern = r'(\w+)\s*(?:\([^)]*\))?\s*(?:{|$)'
        
        matches = re.findall(pattern, query)
        for match in matches:
            if match not in ['query', 'mutation', 'subscription', 'fragment', 'on']:
                fields.append(match)
        
        return list(set(fields))
    
    def _extract_fragments(self, query: str) -> List[str]:
        """Extract fragment names from query."""
        pattern = r'fragment\s+(\w+)\s+on\s+(\w+)'
        matches = re.findall(pattern, query)
        return [f"{name} on {type_name}" for name, type_name in matches]
    
    def _infer_schema_from_operations(self, operations: Dict[str, List[GraphQLOperation]]) -> Dict[str, Any]:
        """Infer GraphQL schema from captured operations."""
        schema = {
            "queries": {},
            "mutations": {},
            "subscriptions": {},
            "types": {},
            "fields": defaultdict(set)
        }
        
        for op_type, ops in operations.items():
            for operation in ops:
                if operation.name:
                    schema[f"{op_type.lower()}s" if op_type != "query" else "queries"][operation.name] = {
                        "fields": operation.fields,
                        "variables": self._infer_variable_types(operation.variables) if operation.variables else {}
                    }
                
                # Track fields
                for field in operation.fields:
                    schema["fields"][field].add(op_type)
        
        return dict(schema)
    
    def _infer_variable_types(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """Infer GraphQL types from variable values."""
        types = {}
        for key, value in variables.items():
            if isinstance(value, bool):
                types[key] = "Boolean"
            elif isinstance(value, int):
                types[key] = "Int"
            elif isinstance(value, float):
                types[key] = "Float"
            elif isinstance(value, str):
                types[key] = "String"
            elif isinstance(value, list):
                if value and isinstance(value[0], str):
                    types[key] = "[String]"
                elif value and isinstance(value[0], int):
                    types[key] = "[Int]"
                else:
                    types[key] = "[Unknown]"
            elif isinstance(value, dict):
                types[key] = "Object"
            else:
                types[key] = "Unknown"
        return types
    
    def _get_unique_operations(self, operations: Dict[str, List[GraphQLOperation]]) -> List[Dict[str, Any]]:
        """Get unique operations with their details."""
        unique = []
        seen = set()
        
        for op_type, ops in operations.items():
            for operation in ops:
                # Create a signature for uniqueness
                sig = f"{op_type}:{operation.name}:{','.join(sorted(operation.fields))}"
                if sig not in seen:
                    seen.add(sig)
                    unique.append({
                        "type": op_type,
                        "name": operation.name,
                        "fields": operation.fields,
                        "example_query": operation.query[:200]
                    })
        
        return unique
    
    def _analyze_common_variables(self, operations: Dict[str, List[GraphQLOperation]]) -> Dict[str, Any]:
        """Analyze common variable patterns."""
        variable_usage = defaultdict(lambda: {"count": 0, "types": set(), "examples": []})
        
        for ops in operations.values():
            for operation in ops:
                if operation.variables:
                    for var_name, var_value in operation.variables.items():
                        variable_usage[var_name]["count"] += 1
                        variable_usage[var_name]["types"].add(type(var_value).__name__)
                        if len(variable_usage[var_name]["examples"]) < 3:
                            variable_usage[var_name]["examples"].append(var_value)
        
        return {
            name: {
                "count": info["count"],
                "types": list(info["types"]),
                "examples": info["examples"]
            }
            for name, info in variable_usage.items()
        }
    
    def _analyze_error_patterns(self, requests: List[CapturedRequest]) -> List[Dict[str, Any]]:
        """Analyze GraphQL error patterns from responses."""
        errors = []
        
        for request in requests:
            response = self.storage.get_response_for_request(request.id)
            if response and response.body_decoded:
                try:
                    data = json.loads(response.body_decoded)
                    if "errors" in data:
                        for error in data["errors"]:
                            errors.append({
                                "message": error.get("message", ""),
                                "code": error.get("extensions", {}).get("code", ""),
                                "path": error.get("path", []),
                                "request_id": request.id
                            })
                except:
                    pass
        
        return errors
    
    def generate_graphql_schema_sdl(self, schema: Dict[str, Any]) -> str:
        """Generate GraphQL SDL from inferred schema."""
        sdl = []
        
        # Generate Query type
        if schema.get("queries"):
            sdl.append("type Query {")
            for name, details in schema["queries"].items():
                args = ""
                if details.get("variables"):
                    arg_list = [f"${k}: {v}" for k, v in details["variables"].items()]
                    args = f"({', '.join(arg_list)})"
                sdl.append(f"  {name}{args}: Unknown")
            sdl.append("}\n")
        
        # Generate Mutation type
        if schema.get("mutations"):
            sdl.append("type Mutation {")
            for name, details in schema["mutations"].items():
                args = ""
                if details.get("variables"):
                    arg_list = [f"${k}: {v}" for k, v in details["variables"].items()]
                    args = f"({', '.join(arg_list)})"
                sdl.append(f"  {name}{args}: Unknown")
            sdl.append("}\n")
        
        # Generate Subscription type
        if schema.get("subscriptions"):
            sdl.append("type Subscription {")
            for name in schema["subscriptions"]:
                sdl.append(f"  {name}: Unknown")
            sdl.append("}\n")
        
        return "\n".join(sdl)
    
    async def perform_introspection(self, endpoint: str, headers: Dict[str, str] = None) -> Optional[GraphQLSchema]:
        """Perform GraphQL introspection on an endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    json={"query": self.introspection_query},
                    headers=headers or {}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "__schema" in data["data"]:
                        return self._parse_introspection_result(data["data"]["__schema"])
            except Exception as e:
                print(f"Introspection failed: {e}")
        
        return None
    
    def _parse_introspection_result(self, schema_data: Dict[str, Any]) -> GraphQLSchema:
        """Parse introspection result into schema object."""
        types = {}
        queries = {}
        mutations = {}
        subscriptions = {}
        scalar_types = set()
        
        for type_data in schema_data.get("types", []):
            type_name = type_data.get("name", "")
            if type_name.startswith("__"):
                continue
            
            types[type_name] = type_data
            
            if type_data.get("kind") == "SCALAR":
                scalar_types.add(type_name)
        
        # Extract operations
        if schema_data.get("queryType"):
            query_type = types.get(schema_data["queryType"]["name"])
            if query_type and query_type.get("fields"):
                for field in query_type["fields"]:
                    queries[field["name"]] = field
        
        if schema_data.get("mutationType"):
            mutation_type = types.get(schema_data["mutationType"]["name"])
            if mutation_type and mutation_type.get("fields"):
                for field in mutation_type["fields"]:
                    mutations[field["name"]] = field
        
        if schema_data.get("subscriptionType"):
            subscription_type = types.get(schema_data["subscriptionType"]["name"])
            if subscription_type and subscription_type.get("fields"):
                for field in subscription_type["fields"]:
                    subscriptions[field["name"]] = field
        
        return GraphQLSchema(
            types=types,
            queries=queries,
            mutations=mutations,
            subscriptions=subscriptions,
            directives=[d["name"] for d in schema_data.get("directives", [])],
            scalar_types=scalar_types
        )