import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    print("No DATABASE_URL found")
    exit(1)

# Connect to database
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Create table
    sql = """
    CREATE TABLE IF NOT EXISTS live_pipeline (
      id INT PRIMARY KEY DEFAULT 1,
      phase TEXT,
      running BOOLEAN,
      mode TEXT,
      status_text TEXT,
      scan_data JSONB,
      score_data JSONB,
      tailor_data JSONB,
      updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    INSERT INTO live_pipeline (id) 
    VALUES (1)
    ON CONFLICT (id) DO NOTHING;
    
    -- Enable Realtime for this table
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'live_pipeline'
      ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE live_pipeline;
      END IF;
    END
    $$;
    """
    
    cur.execute(sql)
    conn.commit()
    print("live_pipeline table created and Realtime enabled successfully!")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
