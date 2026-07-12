import json
import os
import sys
from pymongo import MongoClient

def dump():
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
    db_name = os.environ.get("MONGO_DB", "pcdoctor_swarm")
    
    print(f"Connecting to MongoDB at {mongo_uri}...", file=sys.stderr)
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db["ralfia_agent_messages"]
        
        print("Fetching messages from ralfia_agent_messages...", file=sys.stderr)
        messages = list(collection.find({}, {"_id": 0}))
        print(f"Retrieved {len(messages)} messages.", file=sys.stderr)
        
        output_path = os.path.join(os.path.dirname(__file__), "agent_messages.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        print(f"Saved database dump to {output_path}", file=sys.stderr)
    except Exception as exc:
        print(f"Error dumping MongoDB: {exc}", file=sys.stderr)
        # Fallback to an empty list if Mongo is not running on the build host
        output_path = os.path.join(os.path.dirname(__file__), "agent_messages.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([], f)

if __name__ == "__main__":
    dump()
