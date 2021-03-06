import numpy as np
import sys, os
import matplotlib.pyplot as plt

# to import tools
path2add = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'tools')))
sys.path.append(path2add)
import q5.q5_tools as q5_tools
import q6.q6_tools as q6_tools
import social_network.sn as sn
import q6.sn_environment as sn_env
import q5.gpts_learner as learner

# MAIN PARAMETERS
cum_budget = 10
n_nodes = 100
num_nodes_d = 30
T = 50  # iterations for ts
n_experiments = 50

# create social network and list of D nodes
edges_info, nodes_info, color_map = sn.create_sn(n_nodes)
nodes_d = q5_tools.create_d_nodes(num_nodes_d, n_nodes)
# sn.draw_sn(edges_info[0], nodes_info[0], color_map)

# discretization
cum_budget_base = 10
scale = cum_budget/cum_budget_base
discretized_vector = (scale*np.array([0, 1, 3, 5, 8, 10])).astype(int)  # scale the discretized base vector accordingly

gpts_rewards_per_experiment = []
max_budget_idx_vect = []    # best budget allocation indexes, 1 per experiment
max_value_dict = {}         # dictionary of pair (budget allocation index, value of matching)
opt_dict = {}               # dictionary for optimum (budget allocation index, optimum value of matching)

# obtain a vector of all possible budget allocation
budget_alloc_vect = q5_tools.budget_allocation(discretized_vector, cum_budget)
print("budget alloc vector: ", budget_alloc_vect)

# compute elite nodes with max budget, from which we will choose starting nodes for observing influence spreading
# activation probabilities are unknown and estimated with UCB
seeds_a = q6_tools.select_seeds(cum_budget, n_nodes, edges_info, nodes_info, message="A")
print("seeds a: ", seeds_a)
seeds_b = q6_tools.select_seeds(cum_budget, n_nodes, edges_info, nodes_info, message="B")
print("seeds b: ", seeds_b)
seeds_c = q6_tools.select_seeds(cum_budget, n_nodes, edges_info, nodes_info, message="C")
print("seeds c: ", seeds_c)

# create social network learning environment
env = sn_env.SnEnvironment(seeds_a, seeds_b, seeds_c, nodes_d, nodes_info, edges_info)

for e in range(n_experiments):
    # create gaussian process thompson sampling learner
    gpts_learner = learner.GptsLearner(n_arms=len(budget_alloc_vect))

    # main loop, each step, pull arm, compute reward, fit gp regression
    for t in range(0, T):
        pulled_arm = gpts_learner.pull_arm()  # returns index
        print("arm pulled: ", pulled_arm)
        reward = env.round(budget_alloc_vect[pulled_arm])
        print("reward: ", reward)
        gpts_learner.update(pulled_arm, reward)
        print("means vector: ", gpts_learner.means)

        # update dictionary for optimum matching values
        if not opt_dict.get(pulled_arm):  # if new key, create key-value pair
            opt_dict[pulled_arm] = env.opt()
        else:  # else, do max between old and new optimum
            opt_dict[pulled_arm] = max(env.opt(), opt_dict[pulled_arm])

    # print only one time GPTS confidence intervals
        if (t % (T/5)) == 0 and e == 0:
            q5_tools.print_gp(means=gpts_learner.means, sigmas=gpts_learner.sigmas, x_len=len(budget_alloc_vect))
    if e == 0:
        q5_tools.print_gp(means=gpts_learner.means, sigmas=gpts_learner.sigmas, x_len=len(budget_alloc_vect))

    gpts_rewards_per_experiment.append(gpts_learner.collected_rewards)

    idx = np.argmax(gpts_learner.means)     # index of budget alloc best for this experiment
    max_budget_idx_vect.append(idx)         # append index to list of best budget allocation
    # update dictionary for matching values
    if not max_value_dict.get(idx):       # if new key, create key-value pair
        max_value_dict[idx] = gpts_learner.means[idx]
    else:                               # else, do mean between old and new value
        max_value_dict[idx] = np.mean([gpts_learner.means[idx], max_value_dict[idx]])

max_budget_idx = max(max_budget_idx_vect, key=max_budget_idx_vect.count)    # count the most frequent index
print("Best budget is: ", budget_alloc_vect[max_budget_idx], "with value: ", max_value_dict.get(max_budget_idx))

# printing regret
opt = opt_dict.get(max_budget_idx)
plt.figure()
plt.xlabel("t")
plt.ylabel("Regret")
plt.plot(np.cumsum(opt - np.mean(gpts_rewards_per_experiment, axis=0)), 'g')
plt.show()


