---
comments: true
---

# Ideas on payment

In this document, I will outline some ideas on how to handle payment in the app. This is still a very rough sketch, but might be a good starting point for further discussion. I will try to summarize the problem and then outline some ideas on how to solve it. There seem to be two possible ways to handle payment:

1. The centralized way where everything is handled in chain of trust.
2. The decentralized way where the payment is handled through a blockchain.

I will try to explore both options and then also outline the challenges. Let us get back to the scheme from the [description](description.md) and extend it by the basic idea of money versus results.

``` mermaid
flowchart LR
    id1(Alice) -- json API --- id2[qlued]
    id2[qlued] -- sqooler --- id3[(storage)]
    id3[(storage)] -- sqooler --- id4(Bob)
    id1(Alice) == payment ===> id4(Bob)
```

The challenge is now to integrate payment into this system.

## Some simple ideas on how to integrate payment
The simplest idea is to go with low-tech and allow access to specific users only. This is the traditional way to handle access to a service. However, this is not very flexible and does not allow for a lot of automation. So you would like to be able to charge for the service. Several options are imaginable:

- *Flatrate* If you have large customers they would most likely be interested in a monthly flatrate. This is easy and predicatable. Possibly even very interesting for systems such as simulators. However, they have a massive drawback for the occasional user that would just like to use the system for some specific jobs.
- *Pay per use* This is the most flexible way to handle payment. However, it is also the most complicated to set up and predict the pricing. But it seems likely that this is the way to go at least for the capital intense systems.

Both options are fairly interesting for users and for backend providers. 

## Some ideas on pay per use

The typical usage would be to tie the whole thing together and basically wrap a service like stripe into the service. 
Then you send the job in a trusted way to the person doing the calculation and there you go. 

!!! note
    It could be interesting to have a look how the structure is behind [Polar](https://polar.sh/). They seem to have a similar problem concerning payment between user and service provider.

Most likely it would also have to have the following requirements:

- Alice has to register with some payment options.
- Bob has to register with some payment options.
- The system has to securely send the money from Alice to Bob.
- Alice has to be able to see the cost of a calculation before she submits it. Or does she ?

This brings up the question on how to calculate the estimated costs:

- You might just say that each shot costs some amount of money.
- You might also base the costs on the time the calculation takes this is similiar to the way cloud services are often billed.
- When should be the money transferred ? Most likely some monthly bill would be most reasonable ?
- How can Bob sign his results such that the ownership is clear ? Maybe something like an MD5 hash that includes his username and the json file with the results ? This would be especially important for research groups.

Whatever the case, we really have to enable Bob to register and this brings him back into `qlued`. 

## Some ideas on the decentralized way

As mentionned at the end of the [description](description.md) the system is set up with as much decoupling as possible for the moment. As we have seen Bob can easily change the storage, has no connection with Alice and lives a fairly indpendent life. So you start to wonder if the system could not be transferred to some fancy blockchain infrastructure. The system would then look very roughly like this:

``` mermaid
flowchart LR
    id1(Alice) --- id2[smart contract]
    id2[smart contract] --- id3(Bob)
```

The logic would then be something like this:

- Alice sends a job to the smart contract.
- Bob picks up the job and does the calculation.
- Bob sends the result back to the smart contract and gets paid.

This is tempting in several ways:

- It pushes the decentralization to the most extreme.
- Block-chain systems are all about payment options so the technology sounds like a good fit.
- The whole user registration etc gets fully offloaded to the blockchain with masks etc.
- The whole privacy issue is also simplified due the use of wallets.
- For research groups it could be extra interesting as the ownership of the calculation is very clearly traceble.

The setup obivously also raises a lot of questions. Some of the main questions are:

1. How can Alice make sure that she is the only one that can access the results if she wants them to be private?
1. How can Alice be sure that she receives "good" results?
1. How much are the gas costs? 

If you have any technical input to the questions above you are welcome to contribute to the discussion. Until we have some good draft in this direction we will most likely have to stick to the centralized way.
