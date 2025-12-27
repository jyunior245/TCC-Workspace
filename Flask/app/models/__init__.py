from app.database import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                username VARCHAR(50) UNIQUE NOT NULL,
                email varchar(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """
    )

    conn.commit()
    cur.close()
    conn.close()