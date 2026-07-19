
library("tidyverse")
library("lme4")
library("lmerTest")
library("emmeans")
library("ggplot2")

theme_set(
  theme_bw(base_size = 15) +
    theme(legend.position = "bottom")
)


# LOAD DATA
# data_dir <- "../../data/results/"
data_dir <- "../../data/to_review/"

demographics <- read_csv(paste(data_dir, "demographics.csv", sep = ""))
learning <- read_csv(paste(data_dir, "learning_trials.csv", sep = ""))
testing <- read_csv(paste(data_dir, "test_trials.csv", sep = ""))

learning <- learning %>%
  mutate(
    participant_id = factor(participant_id),
    cover_response = factor(cover_response, levels = c("f", "j"), labels = c("symmetric", "asymmetric")),
    cover_rt = as.numeric(cover_rt),
    cover_correct = as.numeric(cover_correct)
  )

testing <- testing %>%
  mutate(
    participant_id = factor(participant_id),
    rt = as.numeric(rt),
    chosen_position = factor(chosen_position, levels = c("left", "right")),
    confidence_rt = as.numeric(confidence_rt),
    confidence_response = as.numeric(confidence_response),
    confidence_slider_start = as.numeric(confidence_slider_start),
    trial_index = as.numeric(trial_index),
    block_reported = as.numeric(block),
    block = block_reported - 1,
    comparison_type = factor(comparison_type, levels = c("T1", "T0", "T2")),
    correct = as.numeric(correct)
  )


# SET CONSTANTS
blocks <- 4
walk_length <- 48
questions_per_block <- 36
learning_trial_count <- blocks * walk_length
testing_trial_count <- blocks * questions_per_block
t1_block_trial_count <- 24

#--for sanity checks--
og_learning_count <- count(learning) %>% pull(n)
og_testing_count <- count(testing) %>% pull(n)
og_demographics_count <- count(demographics) %>% pull(n)

learning_timeouts <- learning %>%
  group_by(participant_id) %>%
  summarise(
    timeout_rate = sum(!responded) / n()
  ) %>%
  summarise(
    mean_tr = mean(timeout_rate, na.rm = TRUE),
    sd_tr = sd(timeout_rate, na.rm = TRUE),
    min_tr = min(timeout_rate, na.rm = TRUE),
    max_tr = max(timeout_rate, na.rm = TRUE)
  )

testing_timeouts <- testing %>%
  group_by(participant_id) %>%
  summarise(
    timeout_rate = sum(timed_out) / n()
  ) %>%
  summarise(
    mean_tr = mean(timeout_rate, na.rm = TRUE),
    sd_tr = sd(timeout_rate, na.rm = TRUE),
    min_tr = min(timeout_rate, na.rm = TRUE),
    max_tr = max(timeout_rate, na.rm = TRUE)
  )

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
  filter(!is.na(confidence_slider_start)) %>%
  group_by(participant_id) %>%
  summarise(
    slider_cor = cor(confidence_slider_start, confidence_response, use = "complete.obs"),
    n = n()
  ) %>%
  filter(slider_cor >= 0.9) %>%
  pull(participant_id)

# --all together--
excluded_participants <- unique(
  c(
  cover_excl_1, cover_excl_2, cover_excl_3,
  afc_excl_1, afc_excl_2, afc_excl_3,
  conf_excl_1, conf_excl_2, conf_excl_3, conf_excl_4
  )
)
excluded_participants_count <- length(excluded_participants)

# --exclude participants--
learning <- learning %>%
  filter(!participant_id %in% excluded_participants)
testing <- testing %>%
  filter(!participant_id %in% excluded_participants)
demographics <- demographics %>%
  filter(!participant_id %in% excluded_participants)

learning_count <- count(learning) %>% pull(n)
testing_count <- count(testing) %>% pull(n)
demographics_count <- count(demographics) %>% pull(n)

#--sanity check--
# results should be integers, not decimal numbers
cat("participants excluded: ", excluded_participants_count)

cat("OG learning trials: ", og_learning_count)
cat("current learning trials: ", learning_count)
cat("difference: ", og_learning_count - learning_count)
cat("participants excluded in learning: ", (og_learning_count - learning_count) / learning_trial_count)

cat("OG testing trials: ", og_testing_count)
cat("current testing trials: ", testing_count)
cat("difference: ", og_testing_count - testing_count)
cat("participants excluded in testing: ", (og_testing_count - testing_count) / testing_trial_count)

cat("OG demographics count: ", og_demographics_count)
cat("demographics count: ", demographics_count)
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
participants_gender <- demographics %>%
  count(gender) %>%
  mutate(
    prop_gender = n/sum(n)
  )

# Stimulus configuration
participants_graph_config <- demographics %>%
  count(stimulus_config) %>%
  mutate(
    prop_config = n/sum(n)
  )


# PREP DATA FOR ANALYSES
t1_testing <- testing %>%
  filter(comparison_type == "T1")

t1_confidence <- t1_testing %>%
  group_by(participant_id, block) %>%
  summarise(
    block_accuracy = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
    block_avg_rt = mean(rt, na.rm = TRUE)
    )

t1_confdiff <- t1_confidence %>%
  filter(!is.na(confdiff))

t0_confidence <- testing %>%
  group_by(participant_id, block) %>%
  filter(comparison_type != "T0") %>%
  summarise(
    block_accuracy = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )

t2_confidence <- testing %>%
  group_by(participant_id, block) %>%
  filter(comparison_type != "T2") %>%
  summarise(
    block_accuracy = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )


# ANALYSIS 1: LMEM effect of block on accuracy and RT

# ---accuracy---
# approach 1 - use lmer on accuracy per participant/block
# (discarded because summarizing accuracy in a single participant-block row removes information and variance)

# # calc accuracy by block
# accuracy_by_block <- testing %>%
#   filter(comparison_type == "T1") %>%
#   group_by(participant_id, block) %>%
#   summarise(
#     block_accuracy = sum(correct) / n()
#   ) %>%
#   ungroup()


# approach 2 - use glmer on whole table (1 trial/row)
# preferred to keep variance. glmer instead of lmer because response is binary
# note: glmer with (1 + block|participant_id) is ideal but it may not converge, so need to check for isSingular(res_1_a) 
# in such a case there are additional options to be included in the mdoel, but may need to fall back to simpler one
# also check with anova(res_1_b, res_1_a) to see if chisq is significant

# adjust model (1 is preferred, 2 is fallback)
res_1_a1 <- glmer(correct ~ block + (1 + block|participant_id), data = t1_testing, family = binomial)
res_1_a2 <- glmer(correct ~ block + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_1_a2)

# plot
emm_1_a <- emmeans(res_1_a2, ~ block, at = list(block = 0:3), type = "response")
emm_1_a_df <- as.data.frame(emm_1_a)

ggplot() +
  # individual participant points
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = block_accuracy), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  # geom_ribbon(data = emm_1_a_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL), 
  #             alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_1_a_df, aes(x = block, y = prob), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_1_a_df, aes(x = block, y = prob), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Accuracy", x = "Block") +
  theme_minimal()

# see predicted probability of accuracy by block
modeled_acc_by_block <- data.frame(block = 1:4)
modeled_acc_by_block$predicted_prob <- predict(res_1_a2, newdata = modeled_acc_by_block, re.form = NA, type = "response")

# ---rt---
# may need to do log(rt)--need to understand that
res_1_b <- lmer(log(rt) ~ block * comparison_type + (1 + block|participant_id), data = testing)
summary(res_1_b)

# plot
emm_1_b1 <- emmeans(res_1_b, ~ block * comparison_type, at = list(block = 0:3), type = "response")
emm_1_b1_df <- as.data.frame(emm_1_b)
pairs(emm_1_b1)
# this doesn't really show any significant difference between blocks and comparison types, so 
# i will collapse all into a single RT line

emm_1_b2 <- emmeans(res_1_b, ~ block, at = list(block = 0:3), type = "response")
emm_1_b2_df <- as.data.frame(emm_1_b2)

ggplot() +
  # individual participant points, jittered horizontally
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = block_avg_rt), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend on top
  geom_line(data = emm_1_b2_df, aes(x = block, y = response), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_1_b2_df, aes(x = block, y = response), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Reaction Time (ms)", x = "Block") +
  theme_minimal()

# see predicted probability of rt by block
modeled_rt_by_block <- data.frame(block = 1:4)
modeled_rt_by_block$predicted_prob <- predict(res_1_b1, newdata = modeled_rt_by_block, re.form = NA, type = "response")


# ANALYSIS 2: LMEM effect of block on confidence and confdiff

# ---confidence t1---
res_2_a <- lmer(mean_confidence ~ block + (1|participant_id), data = t1_confidence)
summary(res_2_a)

# plot
emm_2_a <- emmeans(res_2_a, ~ block, at = list(block = 0:3), type = "response")
emm_2_a_df <- as.data.frame(emm_2_a)

ggplot() +
  # individual participant points
  geom_jitter(data = participant_df, 
              aes(x = block, y = mean_confidence), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_line(data = emm_2_a_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_2_a_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Confidence", x = "Block") +
  theme_minimal()

# ---confdiff t1---
res_2_b <- lmer(confdiff ~ block + (1|participant_id), data = t1_confdiff)
summary(res_2_b)

# plot
emm_2_b <- emmeans(res_2_b, ~ block, at = list(block = 0:3), type = "response")
emm_2_b_df <- as.data.frame(emm_2_b)

ggplot() +
  # individual participant points
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = confdiff), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_line(data = emm_2_b_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_2_b_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "ConfDiff", x = "Block") +
  theme_minimal()

# ---confidence t0---
res_2_c <- lmer(mean_confidence ~ block + (1|participant_id), data = t0_confidence)
summary(res_2_c)

# plot
emm_2_c <- emmeans(res_2_c, ~ block, at = list(block = 0:3), type = "response")
emm_2_c_df <- as.data.frame(emm_2_c)

ggplot() +
  # individual participant points
  geom_jitter(data = t0_confidence, 
              aes(x = block, y = mean_confidence), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_line(data = emm_2_c_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_2_c_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Confidence", x = "Block") +
  theme_minimal()

# ---t2 confidence---
res_2_d <- lmer(mean_confidence ~ block + (1|participant_id), data = t2_confidence)
summary(res_2_d)

# plot
emm_2_d <- emmeans(res_2_c, ~ block, at = list(block = 0:3), type = "response")
emm_2_d_df <- as.data.frame(emm_2_d)

ggplot() +
  # individual participant points
  geom_jitter(data = t2_confidence, 
              aes(x = block, y = mean_confidence), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_line(data = emm_2_d_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_2_d_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Confidence", x = "Block") +
  theme_minimal()


# ANALYSIS 3: LMEM effect of block n on accuracy at block n+1, controling for accuracy at block n
# at this point the relationship between block and accuracy is not significant, so holding off on this for now


# ANALYSIS 4: LMEM effect of block and destination community on accuracy and RT

res_4_a <- glmer(correct ~ block * correct_dest_community + (1|participant_id), data = t1_testing, family = binomial)
summary(res_4_a)

res_4_b <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id), data = t1_testing)
summary(res_4_b)

# ANALYSIS 5: LMEM effect of block and destination node type on accuracy and RT

res_5_a <- glmer(correct ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing, family = binomial)
summary(res_5_a)

res_5_b <- lmer(log(rt) ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing)
summary(res_5_b)


# ANALYSIS 6: LMEM effect of block on accuracy and RT of learniing phase
res_6_a <- glmer(cover_correct ~ block + (1|participant_id), data = learning, family = binomial)
summary(res_6_a)

res_6_b <- lmer(log(cover_rt) ~ block + (1|participant_id), data = learning)
summary(res_6_b)


# ANALYSIS 7: LMEM effect of block and question category on accuracy and RT
# this was proposed as exploratory, and not with LMEM, only graphs
# need to add levels to comparison pair tag and decide whether using category is better
res_7_a <- glmer(correct ~ block * comparison_pair_tag + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_7_a)

res_7_b <- lmer(log(rt) ~ block * comparison_pair_tag + (1 + block|participant_id), data = testing)
summary(res_7_b)
# this may not be the best approach, maybe test the effect of number or repetitions (either at learning or at testing?)

# ANALYSIS 8: check that graph config is not a confounding factor by re-running main analyses with it as variable

t1_confidence_config <- t1_testing %>%
  group_by(participant_id, block, stimulus_config) %>%
  summarise(
    block_accuracy_config = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
  )

t1_confdiff_config <- t1_confidence_config %>%
  filter(!is.na(confdiff))

res_8_a <- glmer(correct ~ block + stimulus_config + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_8_a)

emmeans(res_8_a, ~ stimulus_config, type = "response")
emm
pairs(emm)

res_8_b <- lmer(log(rt) ~ block  + stimulus_config + (1 + block|participant_id), data = t1_testing)
summary(res_8_b)

res_8_c <- lmer(mean_confidence ~ block + stimulus_config + (1|participant_id), data = t1_confidence_config)
summary(res_2_a)

res_8_d <- lmer(confdiff ~ block + stimulus_config + (1|participant_id), data = t1_confdiff_config)
summary(res_2_b)

