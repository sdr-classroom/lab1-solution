#!/bin/sh

commands="pay 10 jessie\n
get credits jessie\n
exit"

echo $commands

function test_ {

}

function run_test {
    commands=$1
}

(go run cmd/server/main.go config.json > srv_out.txt 2> srv_err.txt; srv_pid=$!) &
(sleep 1 ; echo $commands | go run cmd/client/main.go jessie 3333 > cli_out.txt 2> cli_err.txt; cli_pid=$!) &

sleep 5

pkill -9 -f ".*go-build.*exe/main.*"

echo "done"

# Features to be tested
# - Paying
#   - Paying for self should not create debts or credits to self
#   - Paying for no-one should fail and should not change graph
#   - Paying for two people should evenly distribute debts
#   - 

# function that parses a file
function check_output {

    