# AUTO-Gpt Organization Experiment

A cool AUTO-Gpt experiment. Allowing it to form an orgnazation. Let Agents hire staff with one founder at the helm. 
Still very experimental.

## Example

Here i made the founder a portfolio manager with portfolio X = [BTC, ETH, and SP500]. He proceeded to hire QUANT_A/B/C for each asset, and also a news reporter who kept him up to date with the latest news. 

![alt text](https://i.imgur.com/efaLR9n.jpg)

## Changelog

### Latest Updates

- Wrapped `main.py` in a class and made a `run` function.
- Agents can now hire other instances of agents, who can then hire agents themselves.
- Together they form an organization. Organization handles running all agents and routing messages between them.
- The status of the staff all hired staff added in context and updated every run cycle
- Also kinda added reflexion every N steps (not working yet)


## How to Use

1. Clone the repository.
2. Install dependencies.
3. Run the organization.py script with appropriate parameters (iam still working on making this easy).
4. Enjoy the power of AUTO-GPT Agent.

## Current issues

1. Fix the pinecone implementation

## Future work...
1. Firing agents
2. Fix Staff quitting while their employees are still working (very bad)
3. The Supervisor should be able to change the goals of the employees
4. Fix Reflexion
5. Concurrent Agent Execution (Right now everything runs sequentially)
6. Staff member communications (Could get messy)

## License

All credit goes to the AUTO-GPT author
