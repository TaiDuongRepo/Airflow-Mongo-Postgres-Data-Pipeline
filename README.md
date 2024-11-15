# Lab9

## I. Run MongoDB

Run the following command to start the MongoDB container:

```bash
docker compose -f docker-compose-mongo.yml up -d
```

### Optional: View the MongoDB data

Using the mongo compass, connect to the MongoDB server.

Or use 'mongo-express' container to view the data in the browser.
```yml
services:
  mongodb:
    image: mongo:4.0.8
    container_name: mongodb
    command: mongod --auth
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: admin
      MONGO_INITDB_DATABASE: lab9
      MONGODB_DATA_DIR: /data/db
      MONDODB_LOG_DIR: /dev/null
    ports:
      - "27017:27017"
  mongo-express:
    image: mongo-express
    restart: always
    ports:
      - 8081:8081
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: admin
      ME_CONFIG_MONGODB_URL: mongodb://admin:admin@mongodb:27017/
      ME_CONFIG_BASICAUTH: false
```

View the data in the browser at `http://localhost:8081/`

## II. Run Airflow

Run the following command to start the Airflow and Postgres containers:

```bash
docker compose up --build -d
```

## III. Setup Postgres

### Schema

![Schema](./schema.png)

### Show the tables in the database

1. Execute the following command to connect to the Postgres container:

```bash
docker exec -it airflow-postgres-1 psql -U airflow -d lab9
```

2. Show the tables in the database:

```sql
\dt
```

3. View data in a specific table:

```sql
SELECT * FROM Emails;
```

4. Exit the Postgres container:

```sql
\q
```