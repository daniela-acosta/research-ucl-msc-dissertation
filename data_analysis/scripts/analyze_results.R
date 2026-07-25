
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
    cover_correct = as.numeric(cover_correct),
    block_reported = as.numeric(block),
    block = block_reported - 1
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
    correct = as.numeric(correct),
    confidence = confidence_response / 100
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
    block_avg_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
    )

t1_confidence <- t1_confidence %>%
  arrange(participant_id, block) %>%
  group_by(participant_id) %>%
  mutate(
    prev_confidence = lag(mean_confidence, n = 1),
    prev_confdiff = lag(confdiff, n = 1),
    prev_accuracy = lag(block_accuracy, n = 1)
  ) %>%
  ungroup()

t1_testing_lagged <- t1_testing %>%
  left_join(
    t1_confidence %>% select(participant_id, block, prev_confidence, prev_confdiff, prev_accuracy),
    by = c("participant_id", "block")
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

all_confidence <- testing %>%
  group_by(participant_id, block, comparison_type) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )

learning_by_block <- learning %>%
  group_by(participant_id, block) %>%
  summarise(
    block_accuracy = sum(cover_correct, na.rm = TRUE) / n(),
    block_rt = mean(cover_rt, na.rm = TRUE)
  )

t1_confidence_by_dest_community <- t1_testing %>%
  group_by(participant_id, block, correct_dest_community) %>%
  summarise(
    block_accuracy = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
    block_avg_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
  )

t1_confidence_by_dest_nodetype <- t1_testing %>%
  group_by(participant_id, block, correct_dest_node_type) %>%
  summarise(
    block_accuracy = sum(correct == 1, na.rm = TRUE) / t1_block_trial_count,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
    block_avg_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
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

# adjust model (1 is preferred, 2 is fallback)
# res_1_a1 <- glmer(correct ~ block + (1 + block|participant_id), data = t1_testing, family = binomial) -- didn't converge
res_1_a <- glmer(correct ~ block + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_1_a)
plogis(fixef(res_1_a)["(Intercept)"]) # block 0
plogis(fixef(res_1_a)["(Intercept)"] + fixef(res_1_a)["block"] * 3)  # block 3

# plot
emm_1_a <- emmeans(res_1_a, ~ block, at = list(block = 0:3), type = "response")
emm_1_a_df <- as.data.frame(emm_1_a)

plot1a <- ggplot() +
  # individual participant points
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = block_accuracy), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_ribbon(data = emm_1_a_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_1_a_df, aes(x = block, y = prob), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_1_a_df, aes(x = block, y = prob), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Accuracy", x = "Block") +
  theme_minimal()


# ---rt---
res_1_b1 <- lmer(log(rt) ~ block * comparison_type + (1|participant_id), data = testing)
summary(res_1_b1)

res1b1_speedup <- 1 - exp(fixef(res_1_b1)["block"])
res1b1_speedup_total <- 1 - exp(fixef(res_1_b1)["block"]) ^ 3

res1b1_T1_block0 <- exp(fixef(res_1_b1)["(Intercept)"])
res1b1_T2_block0 <- exp(fixef(res_1_b1)["(Intercept)"] + fixef(res_1_b1)["comparison_typeT2"])

emm_1_b1 <- emmeans(res_1_b1, ~ block * comparison_type, at = list(block = 0:3), type = "response")
emm_1_b1_df <- as.data.frame(emm_1_b1)

plot1b <- ggplot() +
  # individual participant points, split by comparison type
  # geom_jitter(data = testing, 
  #             aes(x = block, y = rt, color = comparison_type),
  #             width = 0.08, height = 0, alpha = 0.06, size = 1) +
  # CI ribbon per group
  geom_ribbon(data = emm_1_b1_df, 
              aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL, 
                  fill = comparison_type, group = comparison_type),
              alpha = 0.15) +
  # model-predicted trend lines
  geom_line(data = emm_1_b1_df, 
            aes(x = block, y = response, color = comparison_type, group = comparison_type),
            linewidth = 1.2) +
  geom_point(data = emm_1_b1_df, 
             aes(x = block, y = response, color = comparison_type),
             size = 2.5) +
  scale_color_manual(values = c("T0" = "darkorange", "T1" = "steelblue", "T2" = "forestgreen"),
                     name = NULL) +
  scale_fill_manual(values = c("T0" = "darkorange", "T1" = "steelblue", "T2" = "forestgreen"), 
                    guide = "none") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Reaction Time (ms)", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom")


# this is for graphs if we only want all T0/T1/T2 together
# res_1_b2 <- lmer(log(rt) ~ block + (1|participant_id), data = testing)
# summary(res_1_b2)
# 
# emm_1_b2 <- emmeans(res_1_b2, ~ block, at = list(block = 0:3), type = "response")
# emm_1_b2_df <- as.data.frame(emm_1_b2)
# 
# # plot
# plot1b <- ggplot() +
#   # individual participant points, jittered horizontally
#   geom_jitter(data = t1_confidence, 
#               aes(x = block, y = block_avg_rt), 
#               width = 0.08, height = 0, 
#               color = "gray50", alpha = 0.5, size = 1.5) +
#   # model-predicted group trend on top
#   geom_ribbon(data = emm_1_b2_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
#               alpha = 0.15, inherit.aes = FALSE) +
#   geom_line(data = emm_1_b2_df, aes(x = block, y = response), 
#             color = "black", linewidth = 1.2) +
#   geom_point(data = emm_1_b2_df, aes(x = block, y = response), 
#              color = "black", size = 2.5) +
#   scale_x_continuous(breaks = 0:3, labels = 1:4) +
#   labs(y = "Reaction Time (ms)", x = "Block") +
#   theme_minimal()

cowplot::plot_grid(plot1a, plot1b, labels = c("A", "B"))

# ---confidence all---
res_1_c <- lmer(mean_confidence ~ block * comparison_type + (1|participant_id), data = all_confidence)
summary(res_1_c)

# plot
emm_1_c <- emmeans(res_1_c, ~ block, at = list(block = 0:3), type = "response")
emm_1_c_df <- as.data.frame(emm_1_c)

plot1c <- ggplot() +
  # individual participant points
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = mean_confidence), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_ribbon(data = emm_1_c_df, aes(x = block, ymin = lower.CL, ymax = upper.CL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_1_c_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_1_c_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Confidence", x = "Block") +
  theme_minimal()

# ---confdiff t1---
res_1_d <- lmer(confdiff ~ block + (1|participant_id), data = t1_confdiff)
summary(res_1_d)

# plot
emm_1_d <- emmeans(res_1_d, ~ block, at = list(block = 0:3), type = "response")
emm_1_d_df <- as.data.frame(emm_1_d)

plot1d <- ggplot() +
  # individual participant points
  geom_jitter(data = t1_confidence, 
              aes(x = block, y = confdiff), 
              width = 0.08, height = 0, 
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_ribbon(data = emm_1_d_df, aes(x = block, ymin = lower.CL, ymax = upper.CL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_1_d_df, aes(x = block, y = emmean), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_1_d_df, aes(x = block, y = emmean), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "ConfDiff", x = "Block") +
  theme_minimal()

# ---"better" plots---
# question -- this was built with the model fit for confidence by correct/incorrect. does it make sense?
# would the line showing the actual data work best? when are fitted menas better than actual means?

res_1_c_bycorrect <- lmer(confidence ~ block * correct + (1|participant_id), data = testing)

emm_bycorrect <- emmeans(res_1_c_bycorrect, ~ block * correct, at = list(block = 0:3))
emm_bycorrect_df <- as.data.frame(emm_bycorrect)

plot1e <- ggplot() +
  geom_ribbon(data = emm_bycorrect_df, 
              aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL, 
                  group = factor(correct), fill = factor(correct)),
              alpha = 0.15) +
  geom_line(data = emm_1_c_df, aes(x = block, y = emmean, color = "Overall"), 
            linewidth = 1.2) +
  geom_point(data = emm_1_c_df, aes(x = block, y = emmean, color = "Overall"), 
             size = 2.5) +
  geom_line(data = emm_bycorrect_df, 
            aes(x = block, y = emmean, color = factor(correct), group = correct), 
            linewidth = 1) +
  geom_point(data = emm_bycorrect_df, 
             aes(x = block, y = emmean, color = factor(correct)), 
             size = 2) +
  scale_color_manual(values = c("0" = "firebrick", "1" = "steelblue", "Overall" = "black"),
                     labels = c("Incorrect", "Correct", "Overall"),
                     name = NULL) +
  scale_fill_manual(values = c("0" = "firebrick", "1" = "steelblue"), guide = "none") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Confidence", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom")

cowplot::plot_grid(plot1e, plot1d, labels = c("A", "B"))

# ANALYSIS 2: LMEM effect of block n on accuracy at block n+1, controling for accuracy at block n
# at this point the relationship between block and accuracy is not significant, so holding off on this for now

res_2_a <- glmer(
  correct ~ prev_confidence + prev_accuracy + (1 | participant_id),
  data = t1_testing_lagged,
  family = binomial
)
summary(res_2_a)

res_2_b <- glmer(
  correct ~ prev_confdiff + prev_accuracy + (1 | participant_id),
  data = t1_testing_lagged,
  family = binomial
)
summary(res_2_b)


# ANALYSIS 3: LMEM effect of block and destination community on accuracy and RT

res_3_a <- glmer(correct ~ block * correct_dest_community + (1|participant_id), data = t1_testing, family = binomial)
summary(res_3_a)

res_3_b <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id), data = t1_testing)
summary(res_3_b)
# looks like W does have a significant change each block for RT. and X's change is different from it (interaction is significant)
# using emtrends now to see difference bwtween slopes

emtrends(res_3_b, ~ correct_dest_community, var = "block")
# looks like X is faster even than W. all results on the log scale! so need to convert before interpreting

# plot
emm_3b <- emmeans(res_3_b, ~ block * correct_dest_community, 
                  at = list(block = 0:3), type = "response")
emm_3b_df <- as.data.frame(emm_3b)

plot3 <- ggplot() +
  # individual participant-level points, faint, split by group
  # geom_jitter(data = t1_testing, 
  #             aes(x = block, y = rt, color = correct_dest_community),
  #             width = 0.08, height = 0, alpha = 0.08, size = 1) +
  # CI ribbon per group
  geom_ribbon(data = emm_4b_df, 
              aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL, 
                  fill = correct_dest_community, group = correct_dest_community),
              alpha = 0.15) +
  # model-predicted trend lines
  geom_line(data = emm_4b_df, 
            aes(x = block, y = response, color = correct_dest_community, 
                group = correct_dest_community),
            linewidth = 1.2) +
  geom_point(data = emm_4b_df, 
             aes(x = block, y = response, color = correct_dest_community),
             size = 2.5) +
  scale_color_manual(values = c("W" = "steelblue", "X" = "firebrick"),
                     labels = c("Within-community (W)", "Cross-community (X)"),
                     name = NULL) +
  scale_fill_manual(values = c("W" = "steelblue", "X" = "firebrick"), guide = "none") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Reaction Time (ms)", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom")

res_3_c <- lmer(mean_confidence ~ block * correct_dest_community + (1|participant_id), data = t1_confidence_by_dest_community)
summary(res_3_c)

res_3_d <- lmer(confdiff ~ block * correct_dest_community + (1|participant_id), data = t1_confidence_by_dest_community)
summary(res_3_d)


# ANALYSIS 4: LMEM effect of block and destination node type on accuracy and RT

res_4_a <- glmer(correct ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing, family = binomial)
summary(res_4_a)

res_4_b <- lmer(log(rt) ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing)
summary(res_4_b)

res_4_c <- lmer(mean_confidence ~ block * correct_dest_node_type + (1|participant_id), data = t1_confidence_by_dest_nodetype)
summary(res_4_c)

res_4_d <- lmer(confdiff ~ block * correct_dest_node_type + (1|participant_id), data = t1_confidence_by_dest_nodetype)
summary(res_4_d)


# ANALYSIS 5: LMEM effect of block on accuracy and RT of learniing phase
res_5_a <- glmer(cover_correct ~ block + (1|participant_id), data = learning, family = binomial)
summary(res_5_a)

res_5_b <- lmer(log(cover_rt) ~ block + (1|participant_id), data = learning)
summary(res_5_b)

emm_5_a <- emmeans(res_5_a, ~ block, at = list(block = 0:3), type = "response")
emm_5_a_df <- as.data.frame(emm_5_a)

emm_5_b <- emmeans(res_5_b, ~ block, at = list(block = 0:3), type = "response")
emm_5_b_df <- as.data.frame(emm_5_b)

plot5a <- ggplot() +
  # individual participant points
  # geom_jitter(data = learning_by_block, 
  #             aes(x = block, y = block_accuracy), 
  #             width = 0.08, height = 0, 
  #             color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_ribbon(data = emm_6_a_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_6_a_df, aes(x = block, y = prob), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_6_a_df, aes(x = block, y = prob), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Accuracy", x = "Block") +
  theme_minimal()

plot5b <- ggplot() +
  # individual participant points
  geom_jitter(data = learning_by_block,
              aes(x = block, y = block_rt),
              width = 0.08, height = 0,
              color = "gray50", alpha = 0.5, size = 1.5) +
  # model-predicted group trend
  geom_ribbon(data = emm_6_b_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_6_b_df, aes(x = block, y = response), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_6_b_df, aes(x = block, y = response), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Reaction Time (ms)", x = "Block") +
  theme_minimal()

# ANALYSIS 6: LMEM effect of block and question category on accuracy and RT
# this was proposed as exploratory, and not with LMEM, only graphs
# need to add levels to comparison pair tag and decide whether using category is better
res_6_a <- glmer(correct ~ block * comparison_pair_tag + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_6_a)

res_7_b <- lmer(log(rt) ~ block * comparison_pair_tag + (1|participant_id), data = testing)
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

emm <- emmeans(res_8_a, ~ stimulus_config, type = "response")
emm
pairs(emm)

res_8_b <- lmer(log(rt) ~ block  + stimulus_config + (1 + block|participant_id), data = t1_testing)
summary(res_8_b)

res_8_c <- lmer(mean_confidence ~ block + stimulus_config + (1|participant_id), data = t1_confidence_config)
summary(res_2_a)

res_8_d <- lmer(confdiff ~ block + stimulus_config + (1|participant_id), data = t1_confdiff_config)
summary(res_2_b)

