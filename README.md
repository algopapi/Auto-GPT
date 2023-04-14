# AUTO-Gpt Organization Experiment

A cool Auto-GPT experiment. Allowing it to form an organization. Let Agents hire staff with one founder at the helm. 
This is a cool glimpse into the world of agent swarms. However, this scheme is still far from perfect and requires a lot of, either manual steering, or other general  improvements. 

## Example

Here I made the founder a portfolio manager with portfolio X = [BTC, ETH, and SP500]. He proceeded to hire QUANT_A/B/C for each asset, and also a news reporter who kept him up to date with the latest news. 
![alt text](https://i.imgur.com/efaLR9n.jpg)


# Main Features
- Auto-gpt's can hire Auto-gpts. Effectively creating an Auto-gpt instance much like a human would. 
- organizations - and the state of agents therein, are saved. This way you can start and stop without having do build the entire org from scratch
- Agents can message either their staff or supervisor. The idea behind this scheme is to prevent to much management overhead. Allowing everyone to communicate with eachother would take up alot of thinking steps.

### Latest Updates
- Added an initial budget to the organization. This prevents agents from overhiring and might give them am incentive to finish there task more efficiently. 
- Hiring employees adds to the running costs, eating away budget faster. 
- The status of the hired staff is added in context and updated every run cycle.
- Impelmented the new promptgenerator. This could be extended with putting agent specific information in the intial prompt. 


## How to Use
1. Clone the repository. (Stable branch)
2. Install dependencies.
3. Run main.py
4. Enjoy the power of AUTO-GPT Agent.

## Current issues

1. Only works with the local cache memory, 
2. The founder messages his supervisor... This should be fixed by removing the command from the prompt for founders
3. The supervisor tends to keep "herassing" the staff. i.e., constantly asking them for updates. (maybe try to add prompts "no micromanagement, etc..")
4. Agents tend to overhire. It might be worth experimenting with prompt instructions. 


## Future work...
1. Give the agents context of the organization they are a part of. They are unaware of that at the moment. This might help align them a bit better. 
2. Fix staff quitting while their employees are still working (very bad)
3. The Supervisor should be able to change the goals of the employees
4. implement reflexion
5. Concurrent Agent Execution (Right now everything runs sequentially)
6. Staff member communications (Could get messy)


## License

All credit goes to the AUTO-GPT author
