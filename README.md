# Real Time AP-XPS Service
This repository maintains a service that will the integrate with Beamline Control System for the new Real Time Ambient Pressure XRay Photon Spectroscopy instrument at the ALS.

# Installation

1. Copy `.env.example` file as `.env` add a very unique key to the `TILED_SINGLE_USER_API_KEY` value.

2. Start services using

```
docker-compose up
```

or if podman-compose is your thing:

```
podman-compose up
```



# Project Documentation
Project documentation is maintained in this repository. This includes:

- [User Stories](./docs/user_strories.md) captures user requirements in story format.

- [Dictionary](./docs/dictionary.md) captures terminology used in this project.

- [System Components](./docs/system_components.md) Describes the components of system maintained in this repository.

- [Design](./docs/design.md) Design notes and diagrams for this system.


# Developer Setup
If you are developing this library, there are a few things to note.

1. Install development dependencies:

```
pip install .[dev]
```

2. Install pre-commit
This step will setup the pre-commit package. After this, commits will get run against flake8, black, isort.

```
pre-commit install
```

3. (Optional) If you want to check what pre-commit would do before commiting, you can run:

```
pre-commit run --all-files
```
