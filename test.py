# Testing features I should have
# - Debts equal credits for given pair of people
# - Graph is simplified
# -


import math
import os
import random
import subprocess
import threading
import time

sleep_speedup = 1

debug = True

def log(*args):
    global debug
    if (debug):
        print(*args)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


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
    # Pre is run before running the commands on the client
    def __init__(self, username=None, pre=None, cmds=[], post=None):
        assert (username == None or isinstance(
            username, str)), "username must be a string"
        self.username = username
        self.hasRun = False
        self.cmds = cmds
        self.outputs = []
        # test is a function that takes the list of outputs, the context, and returns nothing but runs asserts.
        self.post = post
        self.pre = pre

    def __repr__(self):
        return f'CommandBlock(username={self.username}, cmds={self.cmds}, outputs={self.outputs})'


class Outcome:
    def __init__(self, name, desc):
        self.test_name = name
        self.test_desc = desc


class Success(Outcome):
    def __init__(self, name, desc):
        super().__init__(name, desc)


class Failure(Outcome):
    def __init__(self, name, desc, msg):
        super().__init__(name, desc)
        self.msg = msg


class OutcomeLogger:
    def __init__(self):
        self.logs = []

    def logFailure(self, name, desc, msg):
        self.logs.append(Failure(name, desc, msg))

    def logSuccess(self, name, desc):
        self.logs.append(Success(name, desc))

    def print_logs(self):
        for log in self.logs:
            if isinstance(log, Failure):
                print(
                    f"{bcolors.FAIL}[FAILURE]{bcolors.ENDC} {log.test_name}, {log.test_desc} : {log.msg}")
            else:
                print(
                    f"{bcolors.OKGREEN}[SUCCESS]{bcolors.ENDC} {log.test_name}, {log.test_desc}")
        print(f"{len(self.logs)} tests run, {len(list(filter(lambda x: isinstance(x, Failure), self.logs)))} failures.")


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


def write_config_file(filename, graph, port):
    global debug
    with open(filename, 'w') as f:
        debugStr = 'true' if debug else 'false'
        f.write(f'{{"debug": {debugStr}, "port": {port}, "users": [')
        users = []
        for username in graph.keys():
            user = f'{{"username": "{username}", "debts": ['
            debts = []
            for other_user, amount in graph[username].items():
                debts.append(
                    f'{{"username": "{other_user}", "amount": {amount}}}')
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
            assert False, "Amount cannot be parsed as a float"
        if (i == len(lines) - 1):
            assert line.startswith(
                'Total: '), "Last line of `get` must be the total"
            assert math.isclose(
                sum, amount), "Sum of amounts must be equal to the total"
        else:
            sum += amount
            amounts[username] = amount
    return amounts


def run_command_block(clients, cmd_blocks, block):
    cmd_blocks.append(block)
    if (block.pre):
        block.pre()
    if (block.username == None):
        return
    client = clients[block.username]
    subprocess = client.subprocess
    for cmd in block.cmds:
        subprocess.stdin.write((cmd + "\n").encode())
        subprocess.stdin.flush()


def join_client(username):
    p = subprocess.Popen(f"go run cmd/client/main.go {username} 3333",
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         shell=True)
    log(f'Client {username} joined, waiting...')
    time.sleep(0.7 * sleep_speedup)
    return Client(username, p)


def exit_client(client):
    subprocess = client.subprocess
    subprocess.stdin.write('exit\n'.encode())
    subprocess.stdin.write('exit\n'.encode())
    subprocess.stdin.flush()
    log(f'client {client.username} exited, killing it...')
    # time.sleep(0.1 * sleep_speedup)
    # subprocess.kill()
    # time.sleep(0.1 * sleep_speedup)


def parse_outputs(cmd_blocks, clients, context):
    log("Parsing outputs...")
    per_client_outputs = {}
    per_client_lines = {}

    # parse lines for each client
    for client in clients.values():
        log(f'Parsing outputs for client {client.username}...')
        lines = client.subprocess.stdout.readlines()
        log(f"Got lines for client {client.username}")
        lines = [line.decode().strip() for line in lines]
        per_client_lines[client.username] = lines
        per_cmd_outputs = '\n'.join(lines).split('>')
        # filter empty strings
        per_cmd_outputs = list(
            filter(lambda x: x != '', [x.strip() for x in per_cmd_outputs]))
        per_client_outputs[client.username] = per_cmd_outputs

    # assign outputs to blocks
    for block in cmd_blocks:
        outputs = []
        if block.username != None:
            outputs = per_client_outputs[block.username]
        assert (len(block.cmds) <= len(outputs)
                ), "Some command did not produce an output"
        for _ in block.cmds:
            output = outputs[0]
            outputs = outputs[1:]
            block.outputs.append(output)
        if block.post:
            block.post(block.outputs, context)
        # shift the remaining outputs to the next block
        if (block.username != None):
            per_client_outputs[block.username] = outputs


def assert_debts_equal_credits_block(client, owing_user, owed_user):
    def assert_debts_equal_credits(owing_user,
                                   owed_user,
                                   get_debts_output,
                                   get_credits_output):
        owings_debts = parse_get_cmd_output(get_debts_output)
        oweds_credits = parse_get_cmd_output(get_credits_output)
        assert owing_user in oweds_credits, f"User {owing_user} owes money to {owed_user}, but is not listed in the credits of {owed_user}. Actual credits of {owed_user}: {oweds_credits}"
        assert owed_user in owings_debts, f"User {owed_user} that is owed money is not listed as debt to {owing_user}. Actual debts of {owing_user}: {owings_debts}"
        assert oweds_credits[owing_user] == owings_debts[
            owed_user], f"User {owing_user} has debt {owings_debts[owed_user]} to {owed_user}, but user {owed_user} has a credit of {oweds_credits[owing_user]} for {owing_user}"

    return CommandBlock(
        client,
        cmds=[
            f'get debts {owing_user}',
            f'get credits {owed_user}'
        ],
        post=lambda outputs, context: assert_debts_equal_credits(
            owing_user,
            owed_user,
            outputs[0],
            outputs[1]))


def assert_debts_equal_constant_block(client, owing_user, owed_user, expected_amount):
    def assert_debts_equal_credits(owing_user,
                                   owed_user,
                                   get_debts_output,
                                   get_credits_output):
        owings_debts = parse_get_cmd_output(get_debts_output)
        oweds_credits = parse_get_cmd_output(get_credits_output)
        if (expected_amount != 0):
            assert owing_user in oweds_credits, f"User {owing_user} owes money to {owed_user}, but is not listed in the credits of {owed_user}. Actual credits of {owed_user}: {oweds_credits}"
            assert owed_user in owings_debts, f"User {owed_user} that is owed money is not listed as debt to {owing_user}. Actual debts of {owing_user}: {owings_debts}"
            assert oweds_credits[owing_user] == owings_debts[
                owed_user], f"User {owing_user} has debt {owings_debts[owed_user]} to {owed_user}, but user {owed_user} has a credit of {oweds_credits[owing_user]} for {owing_user}"
            assert oweds_credits[owing_user] == expected_amount, f"Amount owed by {owing_user} to {owed_user} is {oweds_credits[owing_user]}, but expected {expected_amount}"
        else:
            assert owed_user not in owings_debts, f"User {owing_user} owes no money to {owed_user}, yet {owed_user} is listed as a debt of {owing_user}."
            assert owing_user not in oweds_credits, f"User {owing_user} owes no money to {owing_user}, yet {owing_user} is listed as a credit of {owed_user}."

    return CommandBlock(
        client,
        cmds=[
            f'get debts {owing_user}',
            f'get credits {owed_user}'
        ],
        post=lambda outputs, context: assert_debts_equal_credits(
            owing_user,
            owed_user,
            outputs[0],
            outputs[1]))


def pay_block(client, amount, all_benefitors):
    def change_expected_totals(outputs, context):
        log(f"{client} pays {amount} for {all_benefitors}")
        expected_totals = context["expected_totals"]
        benefitors = [b for b in all_benefitors if b != client]
        if (benefitors != []):
            per_benefitor_amount = amount / len(benefitors)
            for benefitor in benefitors:
                expected_totals[benefitor] += per_benefitor_amount
            expected_totals[client] -= amount
            log(f"Expected totals: {expected_totals}")

    return CommandBlock(
        client,
        cmds=[f'pay {amount} for {", ".join(all_benefitors)}'],
        post=lambda outputs, context: change_expected_totals(outputs, context))


def get_debts_graph_block(client, users):
    def construct_graph_from_outputs(outputs, context):
        graph = {}
        for i, user in enumerate(users):
            graph[user] = parse_get_cmd_output(outputs[i])
        context["graph"] = graph

    return CommandBlock(
        client,
        cmds=[f'get debts {user}' for user in users],
        post=lambda outputs, context: construct_graph_from_outputs(
            outputs, context)
    )


def get_users_from_graph(graph):
    users = set()
    for username, other_users in graph.items():
        users.add(username)
        for other_user in other_users.keys():
            users.add(other_user)
    # Sorted alphabetically
    users = list(users)
    users.sort()
    return users


def get_debts_per_user(graph):
    debts = {}
    for username in get_users_from_graph(graph):
        debts[username] = 0
    for username, other_users in graph.items():
        for other_user, amount in other_users.items():
            debts[username] += amount
            debts[other_user] -= amount
    return debts


def get_total_per_user(graph):
    totals = {}
    for username in get_users_from_graph(graph):
        totals[username] = 0
    for username, other_users in graph.items():
        for other_user, amount in other_users.items():
            totals[username] += amount
            totals[other_user] -= amount
    return totals


def assert_graph_is_simplified_block():
    # Test that no user is due and owed money
    # Test that the total number of edges is less than the total number of users
    def assert_graph_is_simplified(context):
        graph = context["graph"]
        assert graph != None, "graph is not in context when asserting that it is simplified"
        owing_users = set()
        owed_users = set()
        for user in graph.keys():
            for other_user, amount in graph[user].items():
                # no negative edges
                assert amount >= 0, f"User {user} has a negative debt to {other_user}"
                # no self edges
                assert user != other_user, f"User {user} has a debt to themself"
                owed_users.add(other_user)
                owing_users.add(user)
        # no user is both owing and owed money
        for owing_user in owing_users:
            assert owing_user not in owed_users, f"User {owing_user} is both owing and owed money"

        assert_graph_is_equivalent(context)

    def assert_graph_is_equivalent(context):
        actual_graph = context["graph"]
        expected_totals = context["expected_totals"]
        actual_totals = get_total_per_user(actual_graph)
        for user, expected_total in expected_totals.items():
            assert user in actual_totals, f"User {user} is not in the actual debt graph"
            assert math.isclose(
                expected_total, actual_totals[user], abs_tol=0.001), f"User {user} has a total debt of {actual_totals[user]}, but expected was {expected_total}"

    return CommandBlock(
        None,
        cmds=[],
        post=lambda _, context: assert_graph_is_simplified(context)
    )


def wait_block(duration):
    return CommandBlock(pre=lambda: time.sleep(duration))


def start_server(config_filename, port):
    # use lsof to find the process id of the server listening on the port, then kill it.
    os.system(f'lsof -t -i:{port} | xargs kill')
    log(f"Killed anything listening on {port}")
    srv_cmd = f"go run cmd/server/main.go {config_filename}".split()
    srv_proc = subprocess.Popen(srv_cmd)
    log("Server started, waiting...")
    time.sleep(1 * sleep_speedup)
    return srv_proc


def stop_server(srv_proc, port):
    log("Stopping server...")
    srv_proc.kill()
    # time.sleep(0.1 * sleep_speedup)


# def run_commands(commands, context, username, port):
#     cli_input_filename = 'cli_input.txt'
#     cli_output_filename = 'cli_output.txt'

#     srv_cmd = "go run cmd/server/main.go config.json".split()
#     cli_cmd = f"cat {cli_input_filename} | go run cmd/client/main.go {username} {port} > {cli_output_filename}"

#     input = ''
#     for block in commands:
#         for cmd in block.cmds:
#             input += cmd + '\n'

#     # write input to 'cli_input.txt'
#     with open('cli_input.txt', 'w') as f:
#         f.write(input)

#     # start server
#     srv_proc = subprocess.Popen(srv_cmd)

#     # run client
#     os.system(cli_cmd)

#     time.sleep(1)

#     # read output from 'cli_output.txt'
#     with open('cli_output.txt', 'r') as f:
#         output = f.read()

#     # kill server
#     srv_proc.kill()

#     # Assign outputs to blocks
#     all_outputs = output.strip().split('>')
#     outputs = list(filter(lambda x: x != '', [x.strip() for x in all_outputs]))

#     for block in commands:
#         cmd_count = len(block.cmds)
#         block.outputs = outputs[:cmd_count]
#         outputs = outputs[cmd_count:]
#         block.hasRun = True
#         if block.test:
#             block.test(block.outputs, context)


def matrix_to_graph(matrix):
    n = len(matrix)
    graph = {}
    for i in range(n):
        ui = "user" + str(i)
        graph[ui] = {}
        assert len(matrix[i]) == n, "Matrix must be square"
        for j in range(n):
            uj = "user" + str(j)
            if (matrix[i][j] != 0):
                graph[ui][uj] = matrix[i][j]
    return graph


def run_test_case(logger, test_case):
    print(f"Running test case {test_case.__name__}...")
    
    name = test_case.__name__

    port = None
    srv_proc = None
    context = None
    graph = {}
    command_blocks = []
    connected_clients = {}
    all_clients = {}

    desc = None

    def start_server_wrapper():
        nonlocal port
        nonlocal srv_proc
        nonlocal context

        port = 3333

        config_filename = f"config_{name}.json"
        write_config_file(config_filename, graph, port)

        srv_proc = start_server(config_filename, port)

        expected_total_debts = get_total_per_user(graph)
        context = {"expected_totals": expected_total_debts}

        return srv_proc

    def check_server_started():
        nonlocal srv_proc
        if not srv_proc:
            srv_proc = start_server_wrapper()

    def build_graph(matrix):
        nonlocal graph
        graph = matrix_to_graph(matrix)
        return graph

    def join_client_wrapper(username):
        check_server_started()

        client = join_client(username)
        connected_clients[username] = client
        all_clients[username] = client
        return client

    def exit_client_wrapper(client):
        connected_clients.pop(client.username)
        exit_client(client)

    def run_command_blocks_wrapper(*blocks):
        check_server_started()

        for block in blocks:
            if (block == None):
                continue
            username = block.username
            if (username != None):
                if username not in connected_clients:
                    join_client_wrapper(username)
            run_command_block(connected_clients, command_blocks, block)

    def describe(new_desc):
        nonlocal desc
        desc = new_desc

    try:
        test_case(describe, build_graph, run_command_blocks_wrapper,
                  join_client_wrapper, exit_client_wrapper)

        for client in connected_clients.values():
            exit_client(client)
        connected_clients.clear()

        parse_outputs(command_blocks, all_clients, context)

        stop_server(srv_proc, port)

        logger.logSuccess(name, desc)
    except Exception as e:
        logger.logFailure(name, desc, repr(e))
        stop_server(srv_proc, port)
        # Get type of error
        t = type(e)


def test_case1(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe("Paying someone should create a debt and a credit.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user1', 10, ['user0']),
        assert_debts_equal_constant_block('user0', 'user0', 'user1', 10),
    )


def test_case2(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "Paying someone and oneself should create a debt and a credit only to the other person.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user1', 10, ['user0', 'user1']),
        assert_debts_equal_constant_block('user0', 'user0', 'user1', 10),
    )


def test_case3(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "Paying multiple people including oneself should equally distribute debt.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user0', 20, ['user0', 'user1', 'user2']),
        assert_debts_equal_constant_block('user0', 'user1', 'user0', 10),
        assert_debts_equal_constant_block('user0', 'user2', 'user0', 10),
    )


def test_case4(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe("Paying oneself should change nothing")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user1', 10, ['user1']),
        assert_debts_equal_constant_block('user0', 'user0', 'user1', 0),
    )


def test_case5(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe("Paying someone that then pays back should change nothing")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user0', 10, ['user1']),
        pay_block('user1', 10, ['user0']),
        assert_debts_equal_constant_block('user0', 'user0', 'user1', 0),
        assert_debts_equal_constant_block('user0', 'user1', 'user0', 0),
    )


def test_case6(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "Paying someone that then pays back more should create a debt and a credit.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    run_command_blocks(
        pay_block('user0', 10, ['user1']),
        pay_block('user1', 15, ['user0']),
        wait_block(0.5),
        assert_debts_equal_constant_block('user0', 'user0', 'user1', 5),
        assert_debts_equal_constant_block('user0', 'user1', 'user0', 0),
    )


def test_case7(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "A payment chain of A -> B -> C -> A with all amounts equal should result in no change.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    users = get_users_from_graph(graph)

    run_command_blocks(
        pay_block('user0', 10, ['user1']),
        pay_block('user1', 10, ['user2']),
        pay_block('user2', 10, ['user0']),
        wait_block(0.7),
        get_debts_graph_block('user0', users),
        assert_graph_is_simplified_block(),
    )

def test_case8(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "A payment chain of A -> B -> C with all amounts equal should result in debt from A to C.")

    graph = build_graph([[0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])

    users = get_users_from_graph(graph)

    run_command_blocks(
        pay_block('user0', 10, ['user1']),
        pay_block('user1', 10, ['user2']),
        wait_block(0.7),
        get_debts_graph_block('user0', users),
        assert_graph_is_simplified_block(),
        assert_debts_equal_constant_block('user0', 'user2', 'user0', 10),
    )

def test_case9(describe, build_graph, run_command_blocks, join_client, exit_client):
    describe(
        "After a long sequence of concurrent transactions, the graph should be correct and simplified.")

    graph = build_graph([[0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0]])

    users = get_users_from_graph(graph)

    for i in range(1000) :
        random_user = random.choice(users)
        random_amount = random.randint(1, 10)
        random_benefitors = random.sample(users, random.randint(1, len(users)))
        actual_benefitors = [b for b in random_benefitors if b != random_user]
        total_random_amount = random_amount * len(actual_benefitors)
        run_command_blocks(pay_block(random_user, total_random_amount, random_benefitors))

    run_command_blocks(
        wait_block(1),
        get_debts_graph_block('user0', users),
        assert_graph_is_simplified_block(),
    )


logger = OutcomeLogger()

# run_test_case(logger, test_case1)
# run_test_case(logger, test_case2)
# run_test_case(logger, test_case3)
# run_test_case(logger, test_case4)
# run_test_case(logger, test_case5)
# run_test_case(logger, test_case6)
# run_test_case(logger, test_case7)
# run_test_case(logger, test_case8)
run_test_case(logger, test_case9)
# run_test_case(logger, test_case10)

logger.print_logs()
