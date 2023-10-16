# Testing features I should have
# - Debts equal credits for given pair of people
# - Graph is simplified
# - 


import math
import os
import subprocess
import threading
import time

'''
Fonctionnement d'un test :
- Un test est défini comme une séquence d'actions, où une action est une commande à envoyer au client associée à un test à effectuer sur l'output obtenu, ou une collection d'actions.
- Une fois la séquence d'actions créée, elle peut être fournie à une fonction runner, qui va
    - executer toutes les commandes d'un coup, puis parse l'output pour assigner à chaque commande son output.
    - Ensuite, les fonctions de test seront executées dans l'ordre, sur ces outputs.

En gros, on delay l'execution. On sépare définition des tests, execution, et vérification des outputs en trois phases distinctes. Ceci tout en offrant l'abstraction de pouvoir faire le tout ensemble, notamment executer des vérifications en cours d'execution.

'''
class Client:
    def __init__(self, username, subprocess):
        self.username = username
        self.subprocess = subprocess

class CommandBlock:
    def __init__(self, client = None, cmds = [], post=None):
        self.client = client
        self.hasRun = False
        self.cmds = cmds
        self.outputs = []
        # test is a function that takes the list of outputs, the context, and returns nothing but runs asserts.
        self.post = post
    
    def __repr__(self):
        return f'CommandBlock(username={self.client.username}, cmds={self.cmds}, outputs={self.outputs})'
    
'''
graph = {
    username : {
        username : amount,
        username : amount,
        ...
    },
    ...
}
'''
def write_config_file(filename, graph, port) :
    with open(filename, 'w') as f:
        f.write(f'{{"debug": true, "port": {port}, "users": [')
        users = []
        for username in graph.keys():
            user = f'{{"username": "{username}", "debts": ['
            debts = []
            for other_user, amount in graph[username].items():
                debts.append(f'{{"username": "{other_user}", "amount": {amount}}}')
            user += ', '.join(debts) + ']}'
            users.append(user)
        f.write(', '.join(users) + ']}\n')

'''
output is a dictionary of username -> amount
'''
def parse_get_cmd_output(output):
    amounts = {}
    lines = output.strip().split('\n')
    sum = 0
    for i, line in enumerate(lines):
        if (':' not in line):
            continue
        username, amount = line.split(': ')
        try:
            amount = float(amount)
        except ValueError:
            assert False
        if (i == len(lines) - 1):
            assert line.startswith('Total: ')
            assert math.isclose(sum, amount)
        else:
            sum += amount
            amounts[username] = amount
    return amounts

def run_command_block(cmd_blocks, block):
    cmd_blocks.append(block)
    if (block.client == None):
        return
    subprocess = block.client.subprocess
    for cmd in block.cmds:
        subprocess.stdin.write((cmd + "\n").encode())
        subprocess.stdin.flush()
    time.sleep(0.1)

def join_client(username):
    p = subprocess.Popen(f"go run cmd/client/main.go {username} 3333",
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              shell=True)
    print(f'Client {username} joined, waiting...')
    time.sleep(0.5)
    return Client(username, p)

def exit_client(client):
    subprocess = client.subprocess
    subprocess.stdin.write('exit\n'.encode())
    subprocess.stdin.write('exit\n'.encode())
    subprocess.stdin.flush()
    print(f'client {client.username} exited, killing it...')
    time.sleep(0.5)
    subprocess.kill()
    time.sleep(0.5)

def parse_outputs(cmd_blocks, clients, context):
    print("Parsing outputs...")
    per_client_outputs = {}
    per_client_lines = {}
    for client in clients:
        print(f'Parsing outputs for client {client.username}...')
        lines = client.subprocess.stdout.readlines()
        print(f"Got lines for client {client.username}")
        lines = [line.decode().strip() for line in lines]
        per_client_lines[client.username] = lines
        per_cmd_outputs = '\n'.join(lines).split('>')
        # filter empty strings
        per_cmd_outputs = list(filter(lambda x: x != '', [x.strip() for x in per_cmd_outputs]))
        per_client_outputs[client.username] = per_cmd_outputs
    for block in cmd_blocks:
        client = block.client
        outputs = []
        if (client != None):
            outputs = per_client_outputs[client.username]
        for _ in block.cmds:
            assert len(outputs) > 0
            output = outputs[0]
            outputs = outputs[1:]
            block.outputs.append(output)
        if block.post:
            block.post(block.outputs, context)

def run_assert_debts_equal_credits(client, cmd_blocks, owing_user, owed_user):
    def assert_debts_equal_credits(owing_user,
                                owed_user,
                                get_debts_output,
                                get_credits_output):
        owings_debts = parse_get_cmd_output(get_debts_output)
        oweds_credits = parse_get_cmd_output(get_credits_output)
        assert owing_user in oweds_credits
        assert owed_user in owings_debts
        assert oweds_credits[owing_user] == owings_debts[owed_user]
        
    run_command_block(cmd_blocks, CommandBlock(
        client,
        cmds=[
            f'get debts {owing_user}',
            f'get credits {owed_user}'
        ],
        post=lambda outputs, context: assert_debts_equal_credits(
            owing_user,
            owed_user,
            outputs[0],
            outputs[1])))

def get_users_from_graph(graph) :
    users = set()
    for username, other_users in graph.items():
        users.add(username)
        for other_user in other_users.keys():
            users.add(other_user)
    return users

def get_debts_per_user(graph) :
    debts = {}
    for username in get_users_from_graph(graph):
        debts[username] = 0
    for username, other_users in graph.items():
        for other_user, amount in other_users.items():
            debts[username] += amount
            debts[other_user] -= amount
    return debts

def run_get_debts_graph(client, cmd_blocks, users):
    def construct_graph_from_outputs(outputs, context) :
        graph = {}
        for i, user in enumerate(users):
            graph[user] = parse_get_cmd_output(outputs[i])
        context["graph"] = graph
    
    run_command_block(cmd_blocks, CommandBlock(
        client,
        cmds=[f'get debts {user}' for user in users],
        post=lambda outputs, context: construct_graph_from_outputs(outputs, context)
        ))
    
def run_assert_graph_is_simplified(cmd_blocks):
    # Test that no user is due and owed money
    # Test that the total number of edges is less than the total number of users
    def assert_graph_is_simplified(outputs, context):
        graph = context["graph"]
        owing_users = set()
        owed_users = set()
        for user in graph.keys():
            owing_users.add(user)
            for other_user, amount in graph[user].items():
                # no negative edges
                assert amount >= 0
                # no self edges
                assert user != other_user
                owed_users.add(other_user)
        # no user is both owing and owed money
        for owing_user in owing_users:
            assert owing_user not in owed_users

    run_command_block(cmd_blocks, CommandBlock(
        None,
        cmds=[],
        post=lambda outputs, context: assert_graph_is_simplified(outputs, context)
        ))

def run_payment(client, cmd_blocks, benefitors, amount):
    run_command_block(cmd_blocks, CommandBlock(
        client,
        cmds=[f'pay {amount} for {", ".join(benefitors)}']
        ))

def start_server(config_filename, port):
    # use lsof to find the process id of the server listening on the port, then kill it.
    os.system(f'lsof -t -i:{port} | xargs kill')
    print(f"Killed anything listening on {port}")
    time.sleep(0.5)
    srv_cmd = f"go run cmd/server/main.go {config_filename}".split()
    srv_proc = subprocess.Popen(srv_cmd)
    print("Server started, waiting...")
    time.sleep(1)
    return srv_proc

def stop_server(srv_proc, port):
    print("Stopping server...")    
    srv_proc.kill()
    time.sleep(0.1)

def test_outputs(cmd_blocks) :
    for block in cmd_blocks:
        if block.post:
            block.post(block.outputs, context)

def run_commands(commands, context, username, port):
    cli_input_filename = 'cli_input.txt'
    cli_output_filename = 'cli_output.txt'
    
    srv_cmd = "go run cmd/server/main.go config.json".split()
    cli_cmd = f"cat {cli_input_filename} | go run cmd/client/main.go {username} {port} > {cli_output_filename}"

    input = ''
    for block in commands:
        for cmd in block.cmds:
            input += cmd + '\n'
    
    # write input to 'cli_input.txt'
    with open('cli_input.txt', 'w') as f:
        f.write(input)

    # start server
    srv_proc = subprocess.Popen(srv_cmd)

    # run client
    os.system(cli_cmd)

    time.sleep(1)

    # read output from 'cli_output.txt'
    with open('cli_output.txt', 'r') as f:
        output = f.read()

    # kill server
    srv_proc.kill()

    # Assign outputs to blocks
    all_outputs = output.strip().split('>')
    outputs = list(filter(lambda x: x != '', [x.strip() for x in all_outputs]))

    for block in commands:
        cmd_count = len(block.cmds)
        block.outputs = outputs[:cmd_count]
        outputs = outputs[cmd_count:]
        block.hasRun = True
        if block.test:
            block.test(block.outputs, context)

def plan_commands(planned_blocks, commands, post_test=None) :
    planned_blocks.append(CommandBlock(
        cmds=commands,
        post=post_test))

graph = {
    "jessie": {
        "blake": 30,
        "ollie": 0
    },
    "blake": {
        "jessie": 0,
        "ollie": 5
    },
    "ollie": {
        "jessie": 10,
        "blake": 0
    }
}
users = get_users_from_graph(graph)
port = 3333

command_blocks = []
context = {} # where I can put "variables" in the form of key-value pairs, to be passed from one test to the next.

write_config_file('config.json', graph, port)

start_server('config.json', port)

jessie = join_client('jessie')
blake = join_client('blake')

run_assert_debts_equal_credits(jessie, command_blocks, owing_user='jessie', owed_user='blake')

run_get_debts_graph(jessie, command_blocks, users)
run_assert_graph_is_simplified(command_blocks)

exit_client(jessie)
exit_client(blake)

parse_outputs(command_blocks, [jessie, blake], context)

test_outputs(command_blocks)

'''
srv_cmd = "go run cmd/server/main.go config.json".split()
cli_cmd = "go run cmd/client/main.go jessie 3333".split()

users = [
    "jessie",
    "blake",
    "ollie",
    "parker"
]

srv_proc = subprocess.Popen(srv_cmd)
cli_proc = subprocess.Popen(cli_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

# Define a function to send input to the subprocess and read its output
def send_input(input_str):
    # Send the input to the subprocess
    cli_proc.stdin.write(input_str.encode())
    cli_proc.stdin.flush()

    # Sleep for 0.1 seconds
    time.sleep(0.1)

    # Read the output from the subprocess
    output = cli_proc.stdout.readlines().decode().strip()

    # Return the output
    return output

def parse_debt_output(output):
    # output is multiple lines each of format "<username>: <amount>"
    amounts = {}
    for line in output.split('\n'):
        username, amount = line.split(': ')
        amounts[username] = amount
    return amounts

def get_graph():
    for user in users:
        output = send_input(f'get debts {user}\n')
        

# Send some input to the subprocess and read its output
output = send_input('echo hello\n')
print(output)

# Send some more input to the subprocess and read its output
output = send_input('echo world\n')
print(output)
'''