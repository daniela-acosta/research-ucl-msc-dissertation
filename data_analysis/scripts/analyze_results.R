
library("tidyverse")

theme_set(
  theme_bw(base_size = 15) +
    theme(legend.position = "bottom")
)


# LOAD DATA
demographics <- read_csv("../../data/results/demographics.csv")
learning <- read_csv("../../data/results/learning_trials.csv")
testing <- read_csv("../../data/results/test_trials.csv")

learning <- learning %>%
  mutate(
    participant_id = factor(participant_id),
    cover_response = factor(cover_response, levels = c("f", "j"), labels = c("symmetric", "asymmetric")),
    cover_rt = as.numeric(cover_rt)
  )

testing <- testing %>%
  mutate(
    participant_id = factor(participant_id),
    rt = as.numeric(rt),
    chosen_position = factor(chosen_position, levels = c("left", "right")),
    confidence_rt = as.numeric(confidence_rt),
    confidence_response = as.numeric(confidence_response),
    confidence_slider_start = as.numeric(confidence_slider_start)
  )

glimpse(learning)


# SET CONSTANTS
blocks <- 4
walk_length <- 48
questions_per_block <- 36
learning_trial_count <- blocks * walk_length
testing_trial_count <- blocks * questions_per_block

#--for sanity checks--
og_learning_count <- count(learning) %>% pull(n)
og_testing_count <- count(testing) %>% pull(n)
#--


# IDENTIFY EXCLUSIONS

# --learning trials--
# 1. trials >=90% same response
cover_excl_1 <- learning %>%
  group_by(participant_id, cover_response) %>%
  count() %>%
  filter(n >= learning_trial_count*0.9 ) %>%
  pull(participant_id)

# 2. trials >=90% RT below 200ms
cover_excl_2 <- learning %>%
  group_by(participant_id) %>%
  summarise(
    prop_fast = sum(cover_rt < 200, na.rm = TRUE) / n()
  ) %>%
  filter(prop_fast >= 0.9) %>%
  pull(participant_id)

# 3. RT CV < 0.1
cover_excl_3 <- learning %>%
  group_by(participant_id) %>%
  summarise(
    cover_rt_cv = sd(cover_rt, na.rm = TRUE) / mean(cover_rt, na.rm = TRUE)
  ) %>%
  filter(cover_rt_cv < 0.1) %>%
  pull(participant_id)

# --2afc trials--
# 1. trials >=90% same response
afc_excl_1 <- testing %>%
  group_by(participant_id, chosen_position) %>%
  count() %>%
  filter(n >= testing_trial_count*0.9 ) %>%
  pull(participant_id)

# 2. trials >=90% RT below 300ms
afc_excl_2 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    prop_fast = sum(rt < 300, na.rm = TRUE) / n()
  ) %>%
  filter(prop_fast >= 0.9) %>%
  pull(participant_id)

# 3. RT CV < 0.1
afc_excl_3 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    afc_rt_cv = sd(rt, na.rm = TRUE) / mean(rt, na.rm = TRUE)
  ) %>%
  filter(afc_rt_cv < 0.1) %>%
  pull(participant_id)


# --confidence trials--
# 1. trials >=90% RT below 300ms
conf_excl_1 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    prop_fast = sum(confidence_rt < 300, na.rm = TRUE) / n()
  ) %>%
  filter(prop_fast >= 0.9) %>%
  pull(participant_id)

# 2. RT CV < 0.1
conf_excl_2 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    confidence_rt_cv = sd(confidence_rt, na.rm = TRUE) / mean(confidence_rt, na.rm = TRUE)
  ) %>%
  filter(confidence_rt_cv < 0.1) %>%
  pull(participant_id)

# 3. confidence CV < 0.1
conf_excl_3 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    confidence_cv = sd(confidence_response, na.rm = TRUE) / mean(confidence_response, na.rm = TRUE)
  ) %>%
  filter(confidence_cv < 0.1) %>%
  pull(participant_id)

# 4. correlation start<>response r >= 0.9
conf_excl_4 <- testing %>%
  group_by(participant_id) %>%
  summarise(
    slider_cor = cor(confidence_slider_start, confidence_response, use = "complete.obs")
  ) %>%
  filter(slider_cor >= 0.9) %>%
  pull(participant_id)

# --all together--
excluded_participants <- unique(
  c(
  cover_excl_1, cover_excl_2, cover_excl_3,
  afc_excl_1, afc_excl_1, afc_excl_1,
  conf_excl_1, conf_excl_2, conf_excl_3, conf_excl_4
  )
)
excluded_participants_count <- length(excluded_participants)

# --exclude participants--
learning <- learning %>%
  filter(!participant_id %in% excluded_participants)
testing <- testing %>%
  filter(!participant_id %in% excluded_participants)

learning_count <- count(learning) %>% pull(n)
testing_count <- count(testing) %>% pull(n)

#--sanity check--
cat("participants excluded: ", excluded_participants_count)

cat("OG learning trials: ", og_learning_count)
cat("current learning trials: ", learning_count)
cat("difference: ", og_learning_count - learning_count)
cat("participants excluded in learning: ", (og_learning_count - learning_count) / learning_trial_count)

cat("OG testing trials: ", og_testing_count)
cat("current testing trials: ", testing_count)
cat("difference: ", og_testing_count - testing_count)
cat("participants excluded in testing: ", (og_testing_count - testing_count) / testing_trial_count)
#-----


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


