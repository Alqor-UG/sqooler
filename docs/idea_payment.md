---
comments: true
---

# Ideas on payment

In this document, I will outline some ideas on how to handle payment in the app. This is still a very rough sketch, but might be a good starting point for further discussion. I will try to summarize the problem and then outline some ideas on how to solve it. There seem to be two possible ways to handle payment:

1. The centralized way where everything is handled in chain of trust.
2. The decentralized way where the payment is handled through a blockchain.

I will try to explore both options and then also outline the challenges.
In the following, I will start to draw up the ideas behind a possible decentral solution. Naively, we could think of the following:

 - As a user we have very little interest in the supplier of the calculation. We just want the calculation properly done.
 - As a supplier backend provider or similiar we have little interest in the person demanding the calculation. If you are european you might even be happy to not know too much about them. But you want to get paid for your work and if you are a researcher you want to make sure that it is clear that you made the calculations. 
 
 Until now we might sketch the whole process up like this:

``` mermaid
sequenceDiagram
  autonumber
  actor Alice
  actor Bob
  Alice->>Bob: I want to have a calculation done.
  Bob->>Alice: Send me your instructions according to the configuration.
  Alice->>Bob: Here are my instructions in the json format.
  loop shots
        Bob->>Bob: Verify the instruction!
        Bob->>Bob: Execute the job!
        Bob->>Bob: Save the results in a nice fashion!
  end
  Bob->>Alice: Here are the results.
```

## Some ideas on the decentralized way
This raises the question if it would be possible to make the analogy with block chain technologies with validators and people asking for the validation. The problem is however, that quantum systems are non-deterministic. This kills this analogy to a certain degree. However, maybe something like the minting of NFTs would be a reasonable analogy ?

## Some ideas on the centralized way
The traditional way would be to have Stripe service then together you send the job in a trusted way to the person doing the calculation and there you go.