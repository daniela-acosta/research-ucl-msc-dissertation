
library("tidyverse")

theme_set(
  theme_bw(base_size = 15) +
    theme(legend.position = "bottom")
)

# LOAD DATA
demographics <- read_csv("../../data/results/demographics.csv")
learning <- read_csv("../../data/results/learning_trials.csv")

learning <- learning %>%
  mutate(
    cover_response = factor(cover_response, levels = c("f", "j"), labels = c("symmetric", "asymmetric"))
  )

glimpse(learning)

# IDENTIFY EXCLUSIONS
# learning trials
learning_trial_count <- 192

# 1. trials >=90% same response
# calculate distribution
cover_res_dist <- learning %>%
  group_by(participant_id, cover_response) %>%
  count() 
# filter and extract participants that meet criterion
learning_excl_1 <- cover_res_dist %>%
  filter(n >= learning_trial_count*0.9 ) %>%
  pull(participant_id)

# DESCRIBE PARTICIPANTS
# Age summary
participants_age <- demographics %>% 
  summarise(
    mean_age = mean(age, na.rm = TRUE),
    sd_age = sd(age, na.rm = TRUE),
    min_age = min(age, na.rm = TRUE),
    max_age = max(age, na.rm = TRUE)
  )

# Gender summary

# Stimulus configuration


