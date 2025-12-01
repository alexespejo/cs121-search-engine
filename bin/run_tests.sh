#!/bin/bash

SESSION_NAME="search-engine"

mkdir -p examples/results
mkdir -p examples/errors

# Check if tmux session exists
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? != 0 ]; then
    echo "Creating tmux session '$SESSION_NAME'..."
    tmux new-session -d -s "$SESSION_NAME"
    echo "Session '$SESSION_NAME' created."
else
    echo "Tmux session '$SESSION_NAME' already exists."
fi

tmux send-keys -t "$SESSION_NAME" "source .venv/bin/activate" C-m

if [[ "$1" == "-i" ]]; then
    shift
    tmux send-keys -t "$SESSION_NAME" "python3 run_indexer.py -l warn > examples/results/indexer.result 2> examples/errors/indexer.err" C-m
fi

for testfile in "$@"; do
    test=$(basename $testfile .txt)
    tmux send-keys -t "$SESSION_NAME" "python3 run_search_engine.py < tests/$test.txt > examples/results/$test.result 2> examples/errors/$test.err" C-m
done

echo "Tests Started"