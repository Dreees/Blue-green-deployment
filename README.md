# Blue-Green Deployment with Nginx

This is a simple **Blue-Green Deployment** setup using Docker Compose and Nginx.  
It runs two application containers (**Blue** and **Green**) behind an Nginx reverse proxy that routes traffic to the active version.

---

## How to Run

### Step 1: Clone the project
```
git clone <your-repo-url>
cd <your-repo-folder>
```

### Step 2: Create your .env file
- A sample environment file is provided as .env.example.
- Copy it and modify it with preferred images
```
cp .env.example .env
```
### Step 3: Start the containers
- docker compose up -d

### Step 4: Verify it’s running
- Open your browser and go to:
```
http://<your-vm-ip>
```
### Step 5: Switching Between Blue and Green
#### To switch traffic to the other version:
1. Edit your .env file:
```
ACTIVE_POOL=green
INACTIVE_POOL=blue
```
2. Reload Nginx:
```
docker compose up -d 
```

### Stop and Clean Up
```
docker compose down -v
```