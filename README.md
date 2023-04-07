Made some changes to the AUTO-GPT Agent

=> Wrapped main.py in a class and made a run function
=> Agents can now hire other instances of agents, who can then hire agents themselves. 
=> Together they form an orginazation. Organization handles running all agents and routing messages between them
=> The status of the staff is added in context. 
=> Added reflexion ever N steps. 
