package server

import (
	"fmt"

	"debtManager/internal/common"
)

type Debt struct {
	To     common.Username
	Amount float32
}

type Debts map[common.Username]float32

type Credits map[common.Username]float32

type Graph map[common.Username]Debts

func (g Graph) HasAllUsers(users []common.Username) bool {
	for _, user := range users {
		if _, ok := g[user]; !ok {
			return false
		}
	}
	return true
}

func (g Graph) Pay(owedUser common.Username, owingUsers []common.Username, amount float32) error {
	logger := common.GetGlobalLogger()

	amountPerOwing := amount / float32(len(owingUsers))

	// Remove owed from owing users
	for i := 0; i < len(owingUsers); i++ {
		if owingUsers[i] == owedUser {
			owingUsers[i] = owingUsers[len(owingUsers)-1]
			owingUsers = owingUsers[:len(owingUsers)-1]
			break
		}
	}

	if !g.HasAllUsers(append(owingUsers, owedUser)) {
		return fmt.Errorf("some users are not in the graph")
	}

	if amount < 0 {
		return fmt.Errorf("amount must be positive")
	}

	for _, owingUser := range owingUsers {
		owingUserDebts, ok := g[owingUser]
		if !ok {
			logger.Fatal("owing user not found: " + string(owingUser) + " graph is " + fmt.Sprint(g))
		}
		if owingUser == owedUser {
			logger.Info("user", owingUser, "is paying himself")
			continue
		}
		if _, ok := owingUserDebts[owedUser]; !ok {
			owingUserDebts[owedUser] = amountPerOwing
		} else {
			owingUserDebts[owedUser] += amountPerOwing
		}
	}

	g.SimplifyGraph()

	logger.Info("Graph after payment: ", g)

	return nil
}

func (g Graph) GetDebts(user common.Username) Debts {
	return g[user]
}

func (g Graph) GetCredits(requestedUser common.Username) Credits {
	credits := make(Credits)
	for owingUser, debts := range g {
		if amount, ok := debts[requestedUser]; ok {
			credits[owingUser] = amount
		}
	}
	return credits
}

func (g Graph) SimplifyGraph() {
	// Compute the total amount owed by each user
	owedAmounts := make(map[common.Username]float32)

	for user := range g {
		owedAmounts[user] = 0
	}

	for owingUser, debts := range g {
		for owedUser, amount := range debts {
			owedAmounts[owingUser] += amount
			owedAmounts[owedUser] -= amount
		}
	}

	// Remove all edges of the graph
	for user := range g {
		g[user] = make(Debts)
	}

	// Add edges to the graph greedily
	for owingUser := range g {
		owedAmount := owedAmounts[owingUser]
		if owedAmount <= 0 {
			continue
		}
		for otherUser := range g {
			owedByOther := owedAmounts[otherUser]
			if owedByOther >= 0 {
				continue
			}
			roomForPayment := -owedByOther
			amoutToPay := min(owedAmount, roomForPayment)
			g[owingUser][otherUser] = amoutToPay
			owedAmount -= amoutToPay
			owedAmounts[otherUser] += amoutToPay
			if owedAmount <= 0 {
				break
			}
		}
	}
}
