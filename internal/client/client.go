package client

import (
	"bufio"
	"encoding/gob"
	"fmt"
	"log"
	"net"
	"os"
	"reflect"
	"strconv"
	"strings"

	"github.com/olivierlmr/SDR23F/lab1/internal/common"
	"github.com/olivierlmr/SDR23F/lab1/internal/messages"
)

/*
CLIENT LOGIC
*/

/*
TODO
- One handler function for each user input. It parses user input into a message, sends it, waits for answer, formats response, and returns it.
- "setupClient" which
	- Launches tcp/client goroutine
	- Launches goroutine for listening to client keyboard input. Forwards to handler function.
*/

func StartClient(user common.Username, port string) {
	conn, e := net.Dial("tcp", "127.0.0.1:"+port)
	if e != nil {
		log.Fatalf("Could not connect to server: %s", e)
	}
	defer conn.Close()

	messages.RegisterMessages()

	encoder := gob.NewEncoder(conn)
	decoder := gob.NewDecoder(conn)

	scanner := bufio.NewScanner(os.Stdin)

	fmt.Printf("> ")
	for scanner.Scan() {
		// Reading line from stdin

		line := strings.TrimSpace(scanner.Text())

		args := strings.Split(line, " ")

		//Trim all args
		for i, arg := range args {
			args[i] = strings.TrimSpace(arg)
		}

		switch args[0] {
		case "pay":
			sendPayRequest(args[1:], user, encoder, decoder)
		case "get":
			sendGetRequest(args[1:], user, encoder, decoder)
		case "exit":
			return
		default:
			fmt.Println("Unknown command: " + args[0])
		}

		fmt.Printf("> ")
	}
}

func sendPayRequest(args []string, currentUser common.Username, encoder *gob.Encoder, decoder *gob.Decoder) {
	if len(args) < 2 {
		fmt.Println("Not enough arguments for pay command")
		return
	}
	payer := currentUser
	amount, err := strconv.ParseFloat(args[0], 32)
	if err != nil {
		fmt.Println("Invalid amount for pay command")
		return
	}
	payeesRaw := args[1:]
	payees := make([]common.Username, len(payeesRaw))
	for i, payeeRaw := range payeesRaw {
		payees[i] = common.Username(payeeRaw)
	}

	var msg messages.Message = messages.PayRequest{
		Source:    payer,
		Amount:    float32(amount),
		Receivers: payees,
	}

	err = encoder.Encode(&msg)
	if err != nil {
		panic(err)
	}

	var response messages.Message
	err = decoder.Decode(&response)
	if err != nil {
		panic(err)
	}

	switch response := response.(type) {
	case messages.PayResponse:
		if response.Success {
			fmt.Println("Success")
		} else {
			fmt.Println("Failure")
		}
	case messages.ErrorResponse:
		fmt.Println("Error: ", response.Message)
	default:
		fmt.Println("Unexpected response type: ", reflect.TypeOf(response))
	}
}

func sendGetRequest(args []string, currentUser common.Username, encoder *gob.Encoder, decoder *gob.Decoder) {
	if len(args) < 1 {
		fmt.Println("Not enough arguments for get command")
		return
	}

	var getType messages.GetType
	switch strings.ToLower(args[0]) {
	case "debts":
		getType = messages.Debts
	case "credits":
		getType = messages.Credits
	default:
		fmt.Println("Invalid get type")
		return
	}

	var username common.Username
	switch len(args) {
	case 1:
		username = currentUser
	case 2:
		username = common.Username(args[1])
	default:
		fmt.Println("Too many arguments for get command")
		return
	}

	var msg messages.Message = messages.GetRequest{
		Username: username,
		GetType:  getType,
	}

	err := encoder.Encode(&msg)
	if err != nil {
		panic(err)
	}

	var response messages.Message
	err = decoder.Decode(&response)
	if err != nil {
		panic(err)
	}

	switch response := response.(type) {
	case messages.GetResponse:
		var sum float32 = 0
		for username, amount := range response.Debts {
			fmt.Printf("%s: %f\n", username, amount)
			sum += amount
		}
		fmt.Printf("Total: %f\n", sum)
	case messages.ErrorResponse:
		fmt.Println("Error: ", response.Message)
	default:
		fmt.Println("Unexpected response type: ", reflect.TypeOf(response))
	}
}
