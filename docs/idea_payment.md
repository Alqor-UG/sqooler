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
As you can see the above diagram contains all the necessary steps to get the job done. It was around this idea that `sqooler` was built. However, it does not contain any payment yet and we will have to see how we can integrate it.

## Some simple ideas on how to integrate payment
The simplest idea is to go with low-tech and allow access to specific users only. This is the traditional way to handle access to a service. However, this is not very flexible and does not allow for a lot of automation. So you would like to be able to charge for the service. Several options are imaginable:

- *Flatrate* If you have large customers they would most likely be interested in a monthly flatrate. This is easy and predicatable. Possibly even very interesting for systems such as simulators. However, they have a massive drawback for the occasional user that would just like to use the system for some specific jobs.
- *Pay per use* This is the most flexible way to handle payment. However, it is also the most complicated to set up and predict the pricing. But it seems likely that this is the way to go at least for the capital intense systems.

Both options are fairly interesting for users and for backend providers. Let us alreay make a few notes on the way that the money could flow between Alice and Bob.

## Some ideas on the centralized way
The traditional way would be to have Stripe service then together you send the job in a trusted way to the person doing the calculation and there you go.

## Some ideas on the decentralized way
This raises the question if it would be possible to make the analogy with block chain technologies with validators and people asking for the validation. The problem is however, that quantum systems are non-deterministic. This kills this analogy to a certain degree. However, maybe something like the minting of NFTs would be a reasonable analogy ?

