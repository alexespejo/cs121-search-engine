#!/bin/bash

SESSION_NAME="search-engine"

# Check if tmux session exists
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? != 0 ]; then
    echo "Creating tmux session '$SESSION_NAME'..."
    tmux new-session -d -s "$SESSION_NAME"
    echo "Session '$SESSION_NAME' created."
else
    echo "Tmux session '$SESSION_NAME' already exists."
fi

tmux send-keys -t "$SESSION_NAME" "python3 run_indexer.py" C-m
for test in "$@"; do
    tmux send-keys -t "$SESSION_NAME" "python3 run_search_engine.py < tests/$test.txt &> tests/$test.result" C-m
done

tmux attach -t "$SESSION_NAME"
