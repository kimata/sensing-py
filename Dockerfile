ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-bookworm AS build

RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends --assume-yes \
    build-essential \
    git \
    swig

ENV PATH="/root/.local/bin/:$PATH"

ENV UV_LINK_MODE=copy

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

WORKDIR /opt/sensing_py

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=src,target=src \
    --mount=type=bind,source=.git,target=.git \
    --mount=type=cache,target=/root/.cache/uv \
    git config --global --add safe.directory /opt/sensing_py && \
    uv sync --no-editable --no-group dev

FROM python:${PYTHON_VERSION}-slim-bookworm AS prod

ARG IMAGE_BUILD_DATE
ENV IMAGE_BUILD_DATE=${IMAGE_BUILD_DATE}

ENV TZ=Asia/Tokyo

WORKDIR /opt/sensing_py

COPY --from=build /opt/sensing_py/.venv /opt/sensing_py/.venv

ENV PATH="/opt/sensing_py/.venv/bin:$PATH"

COPY . .

CMD ["sensing"]
