import chromadb
from chromadb.config import Settings
import pandas as pd
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json
from analytics import CMSAnalytics, get_provider_summary_for_rag
import sqlite3
import os

class CMSVectorDatabase:
    """
    Vector database implementation using ChromaDB for CMS Home Health data.
    Supports semantic search and RAG capabilities.
    """
    
    def __init__(self, 
                 chroma_db_path: str = "./chroma_db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 sql_db_path: str = "cms_homehealth.db"):
        
        self.chroma_db_path = chroma_db_path
        self.sql_db_path = sql_db_path
        self.embedding_model_name = embedding_model
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize collections
        self.providers_collection = None
        self.counties_collection = None
        self.create_collections()
        
        # Initialize analytics
        self.analytics = CMSAnalytics(sql_db_path)
    
    def create_collections(self):
        """Create ChromaDB collections for different data types"""
        
        # Providers collection
        self.providers_collection = self.client.get_or_create_collection(
            name="providers",
            metadata={"description": "Home health providers with quality and service information"}
        )
        
        # Counties collection  
        self.counties_collection = self.client.get_or_create_collection(
            name="counties",
            metadata={"description": "County-level statistics and market information"}
        )
        
        # Quality benchmarks collection
        self.benchmarks_collection = self.client.get_or_create_collection(
            name="quality_benchmarks",
            metadata={"description": "Quality benchmarks and comparative statistics"}
        )
    
    def embed_provider_data(self):
        """
        Create embeddings for all providers and store in ChromaDB
        """
        print("Creating embeddings for provider data...")
        
        # Get all providers from SQL database
        providers_query = "SELECT ccn, provider_name, city, state FROM providers"
        providers_df = pd.read_sql_query(providers_query, self.analytics.conn)
        
        documents = []
        metadatas = []
        ids = []
        
        for _, provider in providers_df.iterrows():
            ccn = provider['ccn']
            
            # Generate comprehensive summary for RAG
            summary = get_provider_summary_for_rag(ccn, self.analytics)
            
            if summary:
                documents.append(summary)
                
                # Create metadata
                metadata = {
                    "ccn": ccn,
                    "provider_name": provider['provider_name'],
                    "city": provider['city'],
                    "state": provider['state'],
                    "type": "provider"
                }
                metadatas.append(metadata)
                ids.append(f"provider_{ccn}")
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metadata = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.providers_collection.add(
                documents=batch_docs,
                metadatas=batch_metadata,
                ids=batch_ids
            )
            
        print(f"✓ Embedded {len(documents)} providers")
    
    def embed_county_data(self):
        """
        Create embeddings for county-level market data
        """
        print("Creating embeddings for county market data...")
        
        # Get county statistics
        county_query = "SELECT * FROM county_stats"
        counties_df = pd.read_sql_query(county_query, self.analytics.conn)
        
        documents = []
        metadatas = []
        ids = []
        
        for _, county in counties_df.iterrows():
            if pd.notna(county['county_name']) and pd.notna(county['state_name']):
                
                # Create county summary
                county_summary = f"""
                County: {county['county_name']}, {county['state_name']}
                FIPS Code: {county['fips']}
                Medicare Eligible Population: {county['eligible_population']:,}
                Medicare Enrolled Population: {county['enrolled_population']:,}
                Penetration Rate: {county['penetration_rate']*100:.1f}%
                
                This county has {county['eligible_population']:,} Medicare-eligible residents with 
                {county['enrolled_population']:,} enrolled in Medicare Advantage, representing a 
                {county['penetration_rate']*100:.1f}% penetration rate. This indicates the market 
                size and opportunity for home health services in this area.
                """
                
                documents.append(county_summary.strip())
                
                metadata = {
                    "county_name": county['county_name'],
                    "state_name": county['state_name'],
                    "fips": county['fips'],
                    "eligible_population": int(county['eligible_population']) if pd.notna(county['eligible_population']) else 0,
                    "enrolled_population": int(county['enrolled_population']) if pd.notna(county['enrolled_population']) else 0,
                    "penetration_rate": float(county['penetration_rate']) if pd.notna(county['penetration_rate']) else 0,
                    "type": "county"
                }
                metadatas.append(metadata)
                ids.append(f"county_{county['fips']}")
        
        # Add to collection
        if documents:
            self.counties_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
        print(f"✓ Embedded {len(documents)} counties")
    
    def embed_quality_benchmarks(self):
        """
        Create embeddings for quality benchmark information
        """
        print("Creating embeddings for quality benchmarks...")
        
        # Get national benchmarks
        national_benchmarks = self.analytics.get_quality_benchmarks()
        
        # Create benchmark documents for different contexts
        benchmark_docs = []
        
        # Overall quality distribution
        quality_dist = national_benchmarks['quality_distribution']
        quality_doc = f"""
        National Home Health Quality Distribution:
        
        5-Star Providers (Excellent): {quality_dist['5_star']} providers
        4-Star Providers (Above Average): {quality_dist['4_star']} providers  
        3-Star Providers (Average): {quality_dist['3_star']} providers
        2-Star Providers (Below Average): {quality_dist['2_star']} providers
        1-Star Providers (Poor): {quality_dist['1_star']} providers
        
        National Statistics:
        - Average Quality Score: {national_benchmarks['mean_quality']:.2f}
        - Median Quality Score: {national_benchmarks['median_quality']:.2f}
        - 75th Percentile: {national_benchmarks['percentiles']['75th']:.2f}
        - 90th Percentile: {national_benchmarks['percentiles']['90th']:.2f}
        - 95th Percentile: {national_benchmarks['percentiles']['95th']:.2f}
        
        Use these benchmarks to understand how providers compare nationally.
        High-quality providers typically score 4.0 or above, placing them in the top 25%.
        """
        
        benchmark_docs.append({
            "doc": quality_doc.strip(),
            "metadata": {
                "type": "quality_benchmarks",
                "scope": "national",
                "total_providers": national_benchmarks['total_providers']
            },
            "id": "national_quality_benchmarks"
        })
        
        # Add state-level benchmarks for major states
        major_states = ['CA', 'TX', 'FL', 'NY', 'PA']
        for state in major_states:
            try:
                state_benchmarks = self.analytics.get_quality_benchmarks(state=state)
                if 'error' not in state_benchmarks:
                    state_quality_dist = state_benchmarks['quality_distribution']
                    state_doc = f"""
                    {state} Home Health Quality Distribution:
                    
                    5-Star Providers: {state_quality_dist['5_star']} providers
                    4-Star Providers: {state_quality_dist['4_star']} providers
                    3-Star Providers: {state_quality_dist['3_star']} providers
                    2-Star Providers: {state_quality_dist['2_star']} providers
                    1-Star Providers: {state_quality_dist['1_star']} providers
                    
                    {state} Statistics:
                    - Average Quality Score: {state_benchmarks['mean_quality']:.2f}
                    - Median Quality Score: {state_benchmarks['median_quality']:.2f}
                    - Total Providers: {state_benchmarks['total_providers']}
                    
                    This represents the quality landscape specifically in {state}.
                    """
                    
                    benchmark_docs.append({
                        "doc": state_doc.strip(),
                        "metadata": {
                            "type": "quality_benchmarks",
                            "scope": "state",
                            "state": state,
                            "total_providers": state_benchmarks['total_providers']
                        },
                        "id": f"{state}_quality_benchmarks"
                    })
            except:
                continue
        
        # Add to collection
        for doc_info in benchmark_docs:
            self.benchmarks_collection.add(
                documents=[doc_info["doc"]],
                metadatas=[doc_info["metadata"]],
                ids=[doc_info["id"]]
            )
        
        print(f"✓ Embedded {len(benchmark_docs)} quality benchmark documents")
    
    def semantic_search(self, 
                       query: str, 
                       collection_name: str = "providers",
                       n_results: int = 10,
                       filters: Optional[Dict] = None) -> List[Dict]:
        """
        Perform semantic search across the specified collection
        """
        
        collection = getattr(self, f"{collection_name}_collection")
        
        # Perform search
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filters
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def find_similar_providers(self, ccn: str, n_results: int = 5) -> List[Dict]:
        """
        Find providers similar to a given provider
        """
        
        # Get the provider's summary
        provider_summary = get_provider_summary_for_rag(ccn, self.analytics)
        
        if not provider_summary:
            return []
        
        # Search for similar providers
        results = self.semantic_search(
            query=provider_summary,
            collection_name="providers",
            n_results=n_results + 1,  # +1 because we'll filter out the original
            filters={"ccn": {"$ne": ccn}}  # Exclude the original provider
        )
        
        return results[:n_results]
    
    def rag_query(self, user_question: str, n_context: int = 5) -> Dict[str, Any]:
        """
        Perform RAG (Retrieval-Augmented Generation) query
        Returns relevant context for LLM to generate answer
        """
        
        # Search across all collections
        provider_results = self.semantic_search(user_question, "providers", n_context)
        county_results = self.semantic_search(user_question, "counties", min(n_context, 3))
        benchmark_results = self.semantic_search(user_question, "quality_benchmarks", min(n_context, 2))
        
        # Combine and rank results
        all_results = []
        
        for result in provider_results:
            result['source_type'] = 'provider'
            all_results.append(result)
            
        for result in county_results:
            result['source_type'] = 'county'
            all_results.append(result)
            
        for result in benchmark_results:
            result['source_type'] = 'benchmark'
            all_results.append(result)
        
        # Sort by relevance (distance)
        if all_results and 'distance' in all_results[0] and all_results[0]['distance'] is not None:
            all_results.sort(key=lambda x: x['distance'])
        
        return {
            'query': user_question,
            'context_documents': all_results[:n_context],
            'provider_count': len(provider_results),
            'county_count': len(county_results),
            'benchmark_count': len(benchmark_results)
        }
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the collections"""
        
        stats = {}
        for collection_name in ['providers', 'counties', 'benchmarks']:
            collection = getattr(self, f"{collection_name}_collection")
            stats[collection_name] = collection.count()
        
        return stats
    
    def initialize_vector_database(self):
        """
        Initialize the complete vector database with all embeddings
        """
        print("Initializing CMS Vector Database...")
        print("=" * 50)
        
        # Create embeddings for all data types
        self.embed_provider_data()
        self.embed_county_data() 
        self.embed_quality_benchmarks()
        
        # Display statistics
        stats = self.get_collection_stats()
        
        print("\n" + "=" * 50)
        print("Vector Database Initialization Complete!")
        print(f"Providers embedded: {stats.get('providers', 0)}")
        print(f"Counties embedded: {stats.get('counties', 0)}")
        print(f"Benchmark docs embedded: {stats.get('benchmarks', 0)}")
        print(f"Database location: {self.chroma_db_path}")


def create_sample_rag_queries():
    """
    Create sample queries that demonstrate RAG capabilities
    """
    
    sample_queries = [
        "Find high quality home health providers in Los Angeles County",
        "What are the quality benchmarks for home health agencies?",
        "Show me providers that offer physical therapy in Texas",
        "Which counties have the highest Medicare penetration rates?",
        "Compare quality scores between nonprofit and for-profit providers",
        "Find home health agencies with large patient volumes in Florida",
        "What is the market share of top providers in Cook County, Illinois?",
        "Show quality distribution across different states",
        "Find providers similar to CCN 057001",
        "What services do the top-rated home health agencies offer?"
    ]
    
    return sample_queries


if __name__ == "__main__":
    # Initialize vector database
    vector_db = CMSVectorDatabase()
    
    # Check if we need to initialize
    stats = vector_db.get_collection_stats()
    
    if sum(stats.values()) == 0:
        print("Vector database is empty. Initializing...")
        vector_db.initialize_vector_database()
    else:
        print("Vector database already exists:")
        for collection, count in stats.items():
            print(f"  {collection}: {count} documents")
    
    # Test some sample queries
    sample_queries = create_sample_rag_queries()
    
    print("\nTesting sample RAG queries...")
    for i, query in enumerate(sample_queries[:3]):  # Test first 3
        print(f"\nQuery {i+1}: {query}")
        results = vector_db.rag_query(query, n_context=3)
        print(f"Found {len(results['context_documents'])} relevant documents")
        
        if results['context_documents']:
            top_result = results['context_documents'][0]
            print(f"Top result: {top_result['source_type']} - {top_result['id']}")
    
    vector_db.analytics.close()
