import json

def test_json_extraction():
    test_str = """
    Sure, here is the JSON you requested:
    ```json
    {
      "key": "value",
      "nested": {
        "inner": 1
      }
    }
    ```
    I hope this helps!
    """
    start_idx = test_str.find('{')
    end_idx = test_str.rfind('}') + 1
    
    print("Extracted string:")
    extracted = test_str[start_idx:end_idx]
    print(extracted)
    
    try:
        data = json.loads(extracted)
        print("✅ Parsed successfully:", data)
    except Exception as e:
        print("❌ Failed:", e)

if __name__ == "__main__":
    test_json_extraction()
