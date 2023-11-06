package client

import (
	"bufio"
	"encoding/gob"
	"fmt"
	"log"
	"net"
	"os"
	"reflect"
	"regexp"
	"strconv"
	"strings"

	"debtManager/internal/common"
	"debtManager/internal/messages"
)

func StartClient(user common.Username, hostname string) {
	conn, e := net.Dial("tcp", hostname)
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
	if len(args) < 3 {
		fmt.Println("Not enough arguments for pay command")
		return
	} else if args[1] != "for" {
		fmt.Println("Invalid syntax for pay command. Missing `for` keyword")
		return
	}

	payer := currentUser
	amount, err := strconv.ParseFloat(args[0], 32)
	if err != nil {
		fmt.Println("Invalid amount for pay command")
		return
	}

	payeesConcatted := strings.Join(args[2:], " ")
	re := regexp.MustCompile(` *, +`)
	payeesRaw := re.Split(payeesConcatted, -1)

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
	case "credit":
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
		fmt.Printf("%v", sum)
	case messages.ErrorResponse:
		fmt.Println("Error: ", response.Message)
	default:
		fmt.Println("Unexpected response type: ", reflect.TypeOf(response))
	}
}
