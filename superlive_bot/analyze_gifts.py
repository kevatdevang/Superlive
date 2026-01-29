import json
import os
from collections import defaultdict

def analyze():
    # Path logic similar to Config
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.join(BASE_DIR, 'data', 'gift_analytics.json')
    
    if not os.path.exists(DATA_PATH):
        print(f"❌ File not found: {DATA_PATH}")
        return

    try:
        with open(DATA_PATH, 'r') as f:
            # Handle if file acts as list of objects or individual JSON lines
            # Based on previous code, it's likely appending JSON objects line by line?
            # Or is it a valid JSON array? GiftLog.save() appended?
            # Let's peek at the file format first or handle both.
            # Assuming it's a valid JSON array or Newline Delimited JSON.
            # Let's try reading as text and inferring.
            content = f.read().strip()
            
        data = []
        if content.startswith("[") and content.endswith("]"):
            data = json.loads(content)
        else:
            # Try splitting by newlines if it's NDJSON
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except:
                        pass

        total_gifts = 0
        stream_counts = defaultdict(int)

        for entry in data:
            count = entry.get('gift_count', 0)
            lid = entry.get('livestream_id', 'Unknown')
            
            total_gifts += count
            stream_counts[lid] += count

        print(f"\n📊 **Gift Analytics (Group Wise)**")
        print(f"-----------------------------------")
        print(f"{'Livestream ID':<15} | {'Total Gifts':<10}")
        print(f"----------------|-------------")
        
        sorted_streams = sorted(stream_counts.items(), key=lambda x: x[1], reverse=True)
        for sid, scount in sorted_streams:
             print(f"{sid:<15} | {scount:<10}")

        print(f"-----------------------------------")
        print(f"🎁 **Grand Total:** {total_gifts}")

    except Exception as e:
        print(f"❌ Error analyzing: {e}")

if __name__ == "__main__":
    analyze()
