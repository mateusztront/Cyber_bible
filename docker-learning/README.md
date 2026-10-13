# Docker learning example

The smallest real web app: a page with a button, running inside Docker.
Do these steps once Docker Desktop is installed and running.

## 1. Build the image (turn the recipe into a runnable image)

From inside this folder:

```
docker build -t hello-docker .
```

- `build` = run the Dockerfile recipe
- `-t hello-docker` = name ("tag") the resulting image `hello-docker`
- `.` = "the Dockerfile is in the current folder"

## 2. Run a container from that image

```
docker run -p 8000:8000 hello-docker
```

- `run` = start a container
- `-p 8000:8000` = connect port 8000 on YOUR machine to port 8000 inside
  the container (left = your machine, right = container)

Now open http://localhost:8000 in your browser and press the button.
Press Ctrl+C in the terminal to stop it.

## 3. See what's happening

```
docker images          # list images you've built
docker ps              # list running containers
docker ps -a           # list all containers, including stopped ones
```

## Mental model recap

- Dockerfile (recipe)  --build-->  Image (frozen package)  --run-->  Container (running app)

Once this clicks, Cyber Bible is the same three steps with more libraries,
your real code, and fonts added in.
