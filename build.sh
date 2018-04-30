docker build -t gips --no-cache -f Dockerfile \
    --build-arg UID=$(id -u) \
    --squash .

docker run --rm \
    -v /Users/braswell/repo/gips-rb:/gips \
    -v /Users/braswell/data/gips:/archive \
    gips bash initialize.sh
