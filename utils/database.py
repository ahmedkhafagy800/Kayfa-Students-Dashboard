import streamlit as st
import pandas as pd
from pymongo import MongoClient


@st.cache_resource
def get_mongo_client():
    """Get a cached MongoDB client (singleton pattern).

    This connection lives for the lifetime of the app process - do not
    call client.close() anywhere; Streamlit manages the resource cache.
    """
    mongo_uri = st.secrets["mongo_uri"]
    return MongoClient(mongo_uri)


def get_database():
    """Get the Kayfa database."""
    client = get_mongo_client()
    db_name = st.secrets.get("db_name", "kayfa_analytics")
    return client[db_name]


@st.cache_data(ttl=300)
def _load_data_uncached_errors(collection_name):
    """Load a collection into a DataFrame. Raises on failure instead of
    returning None, so that a transient error (e.g. a Mongo cold start)
    is never cached - st.cache_data would otherwise memoize a `None`
    result and keep serving it until the TTL expires, even after the
    underlying connection recovers.
    """
    db = get_database()
    collection = db[collection_name]
    df = pd.DataFrame(list(collection.find()))
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df


def load_data(collection_name="master_students"):
    """Load data from a MongoDB collection. Returns None and shows an
    st.error on failure. The failure itself is never cached - only
    successful loads are."""
    try:
        return _load_data_uncached_errors(collection_name)
    except Exception as e:
        st.error(f"Error loading {collection_name}: {str(e)}")
        return None


def load_collection(collection_name):
    """Alias for load_data - load a specific collection."""
    return load_data(collection_name)