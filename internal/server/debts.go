package server

import (
	"github.com/olivierlmr/SDR23F/lab1/internal/common"
)

type Debt struct {
	To     common.Username
	Amount float32
}

type Debts map[common.Username]float32

type Credits map[common.Username]float32

type Graph map[common.Username]Debts

func (g Graph) Pay(owedUser common.Username, owingUsers []common.Username, amount float32) {
	logger := common.GetGlobalLogger()

	amountPerOwing := amount / float32(len(owingUsers))
	for _, owingUser := range owingUsers {
		owingUserDebts, ok := g[owingUser]
		if !ok {
			logger.Fatal("owing user not found: " + owingUser)
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
}

func (g Graph) GetDebts(user common.Username) Debts {
	g.SimplifyGraph()
	return g[user]
}

func (g Graph) GetCredits(requestedUser common.Username) Credits {
	g.SimplifyGraph()
	credits := make(Credits)
	for owingUser, debts := range g {
		if amount, ok := debts[requestedUser]; ok {
			credits[owingUser] = amount
		}
	}
	return credits
}

func (g Graph) SimplifyGraph() {
	logger := common.GetGlobalLogger()

	// Compute the total amount owed by each user
	owedAmounts := make(map[common.Username]float32)

	for user := range g {
		owedAmounts[user] = 0
	}

	for owingUser, debts := range g {
		for owedUser, amount := range debts {
			logger.Info(owingUser, "owes", owedUser, amount)
			owedAmounts[owingUser] += amount
			owedAmounts[owedUser] -= amount
			logger.Info(owingUser, "owes", owedUser, amount, "; total owed by", owingUser, ":", owedAmounts[owingUser], "; total owed by", owedUser, ":", owedAmounts[owedUser])
		}
	}

	logger.Info("owedAmounts", owedAmounts)

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
