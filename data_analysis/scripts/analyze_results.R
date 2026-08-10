
library("tidyverse")
library("lme4")
library("lmerTest")
library("emmeans")
library("ggplot2")

theme_set(
  theme_bw(base_size = 15) +
    theme(legend.position = "bottom")
)

# CHECK PACKAGE VERSIONS
# R.version.string
# RStudio.Version()$version
# packageVersion("emmeans")
# packageVersion("lme4")
# packageVersion("lmerTest")
# packageVersion("tidyverse")
# packageVersion("ggplot2")
# # or
# sessionInfo()

# LOAD DATA
# data_dir <- "../../data/results/"
data_dir <- "../../data/to_review/"

demographics <- read_csv(paste(data_dir, "demographics.csv", sep = ""))
learning <- read_csv(paste(data_dir, "learning_trials.csv", sep = ""))
testing <- read_csv(paste(data_dir, "test_trials.csv", sep = ""))
comments <- read_csv(paste(data_dir, "comments_coding_complete.csv", sep = ""))

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
  left_join(
    demographics %>% select(participant_id, age, gender, handedness), 
    by = "participant_id"
    ) %>%
  left_join(
    comments %>% select(participant_id, noticed_arrangement, theme_tags, theme_tags_broad, primary_tag, task_purpose_awareness), 
    by = "participant_id"
  ) %>%
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
    confidence = confidence_response / 100,
    comparison_pair_tag = factor(comparison_pair_tag, 
                                 levels = c("NB1WB__NB2XB", "NB1WNB__NB2XB", 
                                            "NB1WB__NB1WNB", "B2WB__B2XNB", 
                                            "B1WNB__B2WB", "B1WNB__B2XNB",
                                            "B1XB__B2WB", "B1XB__B2XNB",
                                            "B1WNB__B1XB"
                                            ),
                                 labels = c("(1) NB1WB__NB2XB", "(2) NB1WNB__NB2XB", 
                                            "(3) NB1WB__NB1WNB", "(4) B2WB__B2XNB", 
                                            "(5) B1WNB__B2WB", "(6) B1WNB__B2XNB",
                                            "(7) B1XB__B2WB", "(8) B1XB__B2XNB",
                                            "(9) B1WNB__B1XB"
                                            )),
    left_is_correct = case_when(
      comparison_type == "T1" ~ (left_is_option_a & option_a_plausible) | (!left_is_option_a & !option_a_plausible),
      TRUE ~ NA
    ),
    gender = factor(gender),
    handedness = factor(handedness),
    stimulus_config = factor(stimulus_config),
    category = factor(category),
    correct_dest_community = factor(correct_dest_community),
    correct_dest_node_type = factor(correct_dest_node_type),
    theme_tags = factor(theme_tags),
    theme_tags_broad = factor(theme_tags_broad),
    primary_tag = factor(primary_tag, 
                         levels = c("no_guess", "generic_pattern", "relational_transition",
                                    "symmetry_perception", "memory", "reaction_time", "other")),
    noticed_arrangement = factor(noticed_arrangement),
    cumulative_question_views = as.numeric(cumulative_question_views)
  )


# SET CONSTANTS
blocks <- 4
walk_length <- 48
questions_per_block <- 36
learning_trial_count <- blocks * walk_length
testing_trial_count <- blocks * questions_per_block
t1_block_trial_count <- 24

category_colors <- c(
  "(1) NB1WB__NB2XB" = "#1f77b4", 
  "(2) NB1WNB__NB2XB" = "#ff7f0e", 
  "(3) NB1WB__NB1WNB" = "#c893b8", 
  "(4) B2WB__B2XNB" = "#a6a65b", 
  "(5) B1WNB__B2WB" = "#2ca02c", 
  "(6) B1WNB__B2XNB" = "#d62728", 
  "(7) B1XB__B2WB" = "#9467bd", 
  "(8) B1XB__B2XNB" = "#8c564b", 
  "(9) B1WNB__B1XB" = "#5daeb6"
)

#--for sanity checks--
og_learning_count <- count(learning) %>% pull(n)
og_testing_count <- count(testing) %>% pull(n)
og_demographics_count <- count(demographics) %>% pull(n)
og_comments_count <- count(comments) %>% pull(n)

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
comments <- comments %>%
  filter(!participant_id %in% excluded_participants)

learning_count <- count(learning) %>% pull(n)
testing_count <- count(testing) %>% pull(n)
demographics_count <- count(demographics) %>% pull(n)
comments_count <- count(comments) %>% pull(n)

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

all_confidence_by_comptype <- testing %>%
  group_by(participant_id, block, comparison_type) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )

# for analysis 2

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

# for analysis 3

learning_by_block <- learning %>%
  group_by(participant_id, block) %>%
  summarise(
    block_accuracy = sum(cover_correct, na.rm = TRUE) / n(),
    block_rt = mean(cover_rt, na.rm = TRUE)
  )

# for analysis 4

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

# for analysis 5

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

# for analysis 6
all_accuracy_by_cat <- testing %>%
  group_by(participant_id, comparison_pair_tag, block) %>%
  summarise(
    participant_accuracy = mean(correct, na.rm = TRUE),
    participant_rt = mean(rt, na.rm = TRUE),
    participant_confidence = mean(confidence, na.rm = TRUE),
    .groups = "drop") %>%
  group_by(comparison_pair_tag, block) %>%
  summarise(
    mean_accuracy = mean(participant_accuracy),
    se_acc = sd(participant_accuracy) / sqrt(n()),
    mean_rt = mean(participant_rt),
    mean_confidence = mean(participant_confidence),
    .groups = "drop"
  )

t1_accuracy_by_cat <- t1_testing %>%
  group_by(participant_id, comparison_pair_tag, block) %>%
  summarise(
    participant_accuracy = mean(correct, na.rm = TRUE),
    participant_rt = mean(rt, na.rm = TRUE),
    .groups = "drop") %>%
  group_by(comparison_pair_tag, block) %>%
  summarise(
    mean_accuracy = mean(participant_accuracy),
    se_acc = sd(participant_accuracy) / sqrt(n()),
    mean_rt = mean(participant_rt),
    .groups = "drop"
  )

all_confidence_by_questcat <- testing %>%
  group_by(participant_id, block, comparison_pair_tag) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )

t1_confdiff_by_questcat <- t1_testing %>%
  group_by(participant_id, block, comparison_pair_tag) %>%
  summarise(
    trial_n = n(),
    mean_accuracy = sum(correct == 1, na.rm = TRUE) / trial_n,
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
    mean_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
  )

# for analysis 7

dest_community_comparisons <- testing %>%
  filter(is_dest_community_comparison == TRUE)

dest_nodetype_comparisons <- testing %>%
  filter(is_dest_node_type_comparison == TRUE)

# section 2 logic
# overallChoice ~ choiceNode_choiceNode
# inCommon ~ inCommon_different

q1_q2_comparison <- testing %>%
  filter(category == 1 | category == 2) %>%
  mutate(
    within_option_node_type = case_when(
      category == 1 ~ "B",
      category == 2 ~ "NB",
      TRUE ~ NA
    )
  )
# sanity check -- some rows have chosen_community_is_X=NA, this is because of timeouts
q1_q2_comparison %>% group_by(chosen_community_is_X) %>% summarise(n = n())
q1_q2_comparison %>% filter(timed_out == TRUE) %>% group_by(chosen_community_is_X) %>% summarise(n = n())

q3_comparison <- testing %>%
  filter(category == 3)

q5_q6_comparison <- testing %>%
  filter(category == 5 | category == 6) %>%
  mutate(
    implausible_option_node_type = case_when(
      category == 5 ~ "B",
      category == 6 ~ "NB",
      TRUE ~ NA
    ),
    implausible_option_community = case_when(
      category == 5 ~ "W",
      category == 6 ~ "X",
      TRUE ~ NA
    )
  )

q4_comparison <- testing %>%
  filter(category == 4)

q9_comparison <- testing %>%
  filter(category == 9)

# for analysis 8
t1_testing_rescaled <- t1_testing %>%
  mutate(
    age_z = as.numeric(scale(age)),
    session_duration_z = as.numeric(scale(session_duration)),
    cumulative_correct_transition_views_z = as.numeric(scale(cumulative_correct_transition_views)),
    cumulative_base_node_views_z = as.numeric(scale(cumulative_base_node_views)),
    correct_transition_last_view_z = as.numeric(scale(correct_transition_last_view)),
    cumulative_question_views_z = as.numeric(scale(cumulative_question_views))
  )

testing_rescaled <- testing %>%
  mutate(
    age_z = as.numeric(scale(age)),
    session_duration_z = as.numeric(scale(session_duration)),
    cumulative_correct_transition_views_z = as.numeric(scale(cumulative_correct_transition_views)),
    cumulative_base_node_views_z = as.numeric(scale(cumulative_base_node_views)),
    correct_transition_last_view_z = as.numeric(scale(correct_transition_last_view)),
    cumulative_question_views_z = as.numeric(scale(cumulative_question_views))
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
res_1a <- glmer(correct ~ block + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_1a)
plogis(fixef(res_1a)["(Intercept)"]) # block 0
plogis(fixef(res_1a)["(Intercept)"] + fixef(res_1a)["block"] * 3)  # block 3

res_1a2 <- glmer(correct ~ block + (1 |participant_id), data = t1_testing, family = binomial)

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
res_1c <- lmer(mean_confidence ~ block * comparison_type + (1|participant_id), data = all_confidence_by_comptype)
summary(res_1c)

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
res_1d <- lmer(confdiff ~ block + (1|participant_id), data = t1_confdiff)
summary(res_1d)

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

res_2a <- glmer(
  correct ~ prev_confidence + prev_accuracy + (1 | participant_id),
  data = t1_testing_lagged,
  family = binomial
)
summary(res_2a)

res_2b <- glmer(
  correct ~ prev_confdiff + prev_accuracy + (1 | participant_id),
  data = t1_testing_lagged,
  family = binomial
)
summary(res_2b)


# ANALYSIS 3: LMEM effect of block and destination community on accuracy and RT

res_3a <- glmer(correct ~ block * correct_dest_community + (1|participant_id), data = t1_testing, family = binomial)
summary(res_3a)

res_3b <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id), data = t1_testing)
summary(res_3b)
# looks like W does have a significant change each block for RT. and X's change is different from it (interaction is significant)
# using emtrends now to see difference bwtween slopes

# pool 8 -> 8 instances per question. categories 2,5,8.
# this is to check whether the finding that participants respond to X transition questions 
# faster still stands. this is to account for the recency (priming) effect
t1_pool8 <- subset(t1_testing, category %in% c(2, 5, 8))
res_pool8 <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id) + (1|question_code), data = t1_pool8)
summary(res_pool8)

res_cat7 <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id) + (1|question_code),
                 data = subset(t1_testing, category == 7))
summary(res_cat7)

res_cats16 <- lmer(log(rt) ~ block * correct_dest_community + (1|participant_id) + (1|question_code), data = subset(t1_testing, category %in% c(1, 6)))
summary(res_cats16)

emtrends(res_3b, ~ correct_dest_community, var = "block")
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

res_3c <- lmer(mean_confidence ~ block * correct_dest_community + (1|participant_id), data = t1_confidence_by_dest_community)
summary(res_3c)

res_3d <- lmer(confdiff ~ block * correct_dest_community + (1|participant_id), data = t1_confidence_by_dest_community)
summary(res_3d)


# ANALYSIS 4: LMEM effect of block and destination node type on accuracy and RT

res_4a <- glmer(correct ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing, family = binomial)
summary(res_4a)

res_4_b <- lmer(log(rt) ~ block * correct_dest_node_type + (1|participant_id), data = t1_testing)
summary(res_4_b)

res_4_c <- lmer(mean_confidence ~ block * correct_dest_node_type + (1|participant_id), data = t1_confidence_by_dest_nodetype)
summary(res_4_c)

res_4_d <- lmer(confdiff ~ block * correct_dest_node_type + (1|participant_id), data = t1_confidence_by_dest_nodetype)
summary(res_4_d)


res_4a2 <- glmer(correct ~ block + correct_dest_node_type + (1|participant_id), data = t1_testing, family = binomial)
summary(res_4a2)


# ANALYSIS 5: LMEM effect of block on accuracy and RT of learniing phase
res_5a <- glmer(cover_correct ~ block + (1|participant_id), data = learning, family = binomial)
summary(res_5a)

res_5b <- lmer(log(cover_rt) ~ block + (1|participant_id), data = learning)
summary(res_5b)

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
  geom_ribbon(data = emm_5_a_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_5_a_df, aes(x = block, y = prob), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_5_a_df, aes(x = block, y = prob), 
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
  geom_ribbon(data = emm_5_b_df, aes(x = block, ymin = asymp.LCL, ymax = asymp.UCL),
              alpha = 0.15, inherit.aes = FALSE) +
  geom_line(data = emm_5_b_df, aes(x = block, y = response), 
            color = "black", linewidth = 1.2) +
  geom_point(data = emm_5_b_df, aes(x = block, y = response), 
             color = "black", size = 2.5) +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Reaction Time (ms)", x = "Block") +
  theme_minimal()

cowplot::plot_grid(plot5a, plot5b, labels = c("A", "B"))

# ANALYSIS 6: LMEM effect of block and question category on accuracy and RT
# this was proposed as exploratory, and not with LMEM, only graphs
# need to add levels to comparison pair tag and decide whether using category is better
res_6a <- glmer(correct ~ block * comparison_pair_tag + (1 |participant_id), data = t1_testing, family = binomial)
summary(res_6a)

res_6a_coefs <- as.data.frame(summary(res_6a)$coefficients)
res_6a_cat_rows <- res_6a_coefs[grepl("comparison_pair_tag", rownames(res_6a_coefs)), ]
res_6a_cat_rows$p_adj_holm <- p.adjust(res_6a_cat_rows$`Pr(>|z|)`, method = "holm")

# graph of raw data

plot6a <- ggplot(t1_accuracy_by_cat, aes(x = block, y = mean_accuracy, 
                                           color = comparison_pair_tag, group = comparison_pair_tag)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  # geom_errorbar(aes(ymin = mean_accuracy - se, ymax = mean_accuracy + se), width = 0.1) +
  scale_color_manual(values = category_colors, name = "Question category") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Mean Accuracy", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom")
# not sure if error bars should be added or not, as this is exploratory and they seem to just add noise


res_6b <- lmer(log(rt) ~ block * comparison_pair_tag + (1|participant_id), data = testing)
summary(res_6b)

res_6b_coefs <- as.data.frame(summary(res_6b)$coefficients)
res_6b_cat_rows <- res_6b_coefs[grepl("comparison_pair_tag", rownames(res_6b_coefs)), ]
res_6b_cat_rows$p_adj_holm <- p.adjust(res_6b_cat_rows$`Pr(>|t|)`, method = "holm")

plot6b <- ggplot(all_accuracy_by_cat, aes(x = block, y = mean_rt, 
                                         color = comparison_pair_tag, group = comparison_pair_tag)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = category_colors, name = "Question category") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Mean Reactoin Time (ms)", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom") + 
  guides(color = guide_legend(nrow = 2))


res_6c <- lmer(mean_confidence ~ block * comparison_pair_tag + (1|participant_id), data = all_confidence_by_questcat)
summary(res_6c)

plot6c <- ggplot(all_accuracy_by_cat, aes(x = block, y = mean_confidence, 
                                          color = comparison_pair_tag, group = comparison_pair_tag)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = category_colors, name = "Question category") +
  scale_x_continuous(breaks = 0:3, labels = 1:4) +
  labs(y = "Mean Reactoin Time (ms)", x = "Block") +
  theme_minimal() +
  theme(legend.position = "bottom") + 
  guides(color = guide_legend(nrow = 2))

res_6d <- lmer(confdiff ~ block * comparison_pair_tag + (1|participant_id), data = t1_confdiff_by_questcat)
summary(res_6d)

res_6d_coefs <- as.data.frame(summary(res_6d)$coefficients)
res_6d_cat_rows <- res_6d_coefs[grepl("comparison_pair_tag", rownames(res_6d_coefs)), ]
res_6d_cat_rows$p_adj_holm <- p.adjust(res_6d_cat_rows$`Pr(>|t|)`, method = "holm")

# check distribution of nan's for confdiff by question
sum(is.nan(t1_confdiff_by_questcat$confdiff)) / nrow(t1_confdiff_by_questcat)

t1_confdiff_by_questcat %>%
  group_by(comparison_pair_tag, block) %>%
  summarise(n_nan = sum(is.nan(confdiff)), n_total = n(), .groups = "drop") %>%
  mutate(pct_nan = n_nan / n_total)


# ANALYSIS 7: effects of structural characteristics on choice bias

res_7a <- glmer(chosen_community_is_X ~ block * comparison_type + (1|participant_id), data = dest_community_comparisons, family = binomial)
summary(res_7a)
plogis(fixef(res_7a)["(Intercept)"]) # predicted rate at block 1
plogis(fixef(res_7a)["(Intercept)"] + fixef(res_7a)["block"] * 3)

res_7b <- glmer(chosen_nodetype_is_B ~ block * comparison_type + (1|participant_id), data = dest_nodetype_comparisons, family = binomial)
summary(res_7b)
plogis(fixef(res_7b)["(Intercept)"]) # predicted rate at block 1
plogis(fixef(res_7b)["(Intercept)"] + fixef(res_7b)["block"] * 3)

# investigating node type preference
# comparing q1/q2
res_7c <- glmer(chosen_community_is_X ~ block * within_option_node_type + (1|participant_id), data = q1_q2_comparison, family = binomial)
summary(res_7c)
plogis(fixef(res_7c)["(Intercept)"]) 
plogis(fixef(res_7c)["(Intercept)"] + fixef(res_7c)["block"] * 3) 

#comparing q3/chance
res_7d <- glmer(chosen_nodetype_is_B ~ block + (1|participant_id), data = q3_comparison, family = binomial)
summary(res_7d)
plogis(fixef(res_7d)["(Intercept)"]) 
plogis(fixef(res_7d)["(Intercept)"] + fixef(res_7d)["block"] * 3) 
# no significant results, consistent with findings from analysis 3

# investigating community preference
# comparing q4/chance
res_7e <- glmer(chosen_nodetype_is_B ~ block + (1|participant_id), data = q4_comparison, family = binomial)
summary(res_7e)
plogis(fixef(res_7e)["(Intercept)"]) 
plogis(fixef(res_7e)["(Intercept)"] + fixef(res_7e)["block"] * 3) 

# comparing q9/chance
res_7f <- glmer(chosen_nodetype_is_B ~ block + (1|participant_id), data = q9_comparison, family = binomial)
summary(res_7f)
plogis(fixef(res_7f)["(Intercept)"]) 
plogis(fixef(res_7f)["(Intercept)"] + fixef(res_7f)["block"] * 3) 
#no significant results here either :'(

# ANALYSIS 8: omnibus test

all_confidence_omnibus <- testing_rescaled %>%
  group_by(participant_id, 
           block, 
           comparison_type, 
           # category,
           stimulus_config, 
           options_adjacent, 
           # cumulative_correct_transition_views_z,
           cumulative_base_node_views_z,
           # correct_transition_last_view_z,
           # correct_dest_community,
           # correct_dest_node_type,
           # left_is_correct,
           confidence_slider_start,
           age_z,
           gender,
           handedness,
           session_duration_z
           ) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100
  )

all_confdiff_omnibus <- testing_rescaled %>%
  filter(comparison_type == "T1") %>%
  group_by(participant_id, 
           block, 
           # category,
           stimulus_config, 
           # options_adjacent, 
           cumulative_correct_transition_views_z,
           cumulative_base_node_views_z,
           # correct_transition_last_view_z,
           # correct_dest_community,
           # correct_dest_node_type,
           # left_is_correct,
           confidence_slider_start,
           # age_z,
           # gender,
           # handedness,
           # session_duration_z
  ) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
  ) %>%
  filter(!is.na(confdiff))
# the length of non na in confdiff is so small that an omnibus test is not worth it i think

all_confdiff_omnibus <- all_confidence_omnibus %>%
  filter(comparison_type == "T1") %>%
  filter(!is.na(confdiff))

res_8a <- glmer(correct ~ 
                  stimulus_config +
                  block * category + 
                  options_adjacent +
                  cumulative_correct_transition_views_z +
                  cumulative_base_node_views_z +
                  correct_transition_last_view_z +
                  correct_dest_community +
                  correct_dest_node_type + 
                  left_is_correct +
                  session_duration_z +
                  (1|participant_id),
                data = t1_testing_rescaled, family = binomial
                  )
summary(res_8a)
1-exp(fixef(res_8a)["correct_transition_last_view_z"]) # using exp here because it's a continuous predictor
# 4.9% decrease in odds of accurate answer for every 1 SD increase in recency gap

res_8a2 <- glmer(correct ~ block + cumulative_correct_transition_views_z + cumulative_question_views_z + (1|participant_id), data = t1_testing_rescaled, family = binomial)
summary(res_8a2)

# translate sd into something meaningful
testing_rescaled %>% 
  summarise(
    mean = mean(correct_transition_last_view, na.rm = TRUE),
    sd = sd(correct_transition_last_view, na.rm = TRUE),
    min = min(correct_transition_last_view, na.rm = TRUE),
    q25 = quantile(correct_transition_last_view, 0.25, na.rm = TRUE),
    q75 = quantile(correct_transition_last_view, 0.75, na.rm = TRUE),
    max = max(correct_transition_last_view, na.rm = TRUE)
  )

exp(fixef(res_8a)["cumulative_correct_transition_views_z"])
# 14.7% increase in odds of accuracy for every 1 SD change in amount of views

# translate sd into something meaningful
testing_rescaled %>% 
  summarise(
    mean = mean(cumulative_correct_transition_views, na.rm = TRUE),
    sd = sd(cumulative_correct_transition_views, na.rm = TRUE),
    min = min(cumulative_correct_transition_views, na.rm = TRUE),
    q25 = quantile(cumulative_correct_transition_views, 0.25, na.rm = TRUE),
    q75 = quantile(cumulative_correct_transition_views, 0.75, na.rm = TRUE),
    max = max(cumulative_correct_transition_views, na.rm = TRUE)
  )

exp(fixef(res_8a)["cumulative_base_node_views_z"])
# 22.2% increase in odds of accuracy for every 1 SD change in node views

# odds = probability / (1 - probability)

# odds_ratio_to_prob <- function(p0, OR) {
#   odds0 <- p0 / (1 - p0)
#   odds1 <- odds0 * OR
#   p1 <- odds1 / (1 + odds1)
#   return(p1)
# }
# 
# # example: your cumulative_correct_transition_views_z finding, starting from 52.1%
# odds_ratio_to_prob(0.521, exp(0.137386))

testing_rescaled %>% 
  summarise(
    mean = mean(cumulative_base_node_views, na.rm = TRUE),
    sd = sd(cumulative_base_node_views, na.rm = TRUE),
    min = min(cumulative_base_node_views, na.rm = TRUE),
    q25 = quantile(cumulative_base_node_views, 0.25, na.rm = TRUE),
    q75 = quantile(cumulative_base_node_views, 0.75, na.rm = TRUE),
    max = max(cumulative_base_node_views, na.rm = TRUE)
  )


res_8a_coefs <- as.data.frame(summary(res_8a)$coefficients)
res_8a_cat_rows <- res_8a_coefs
res_8a_cat_rows$p_adj_holm <- p.adjust(res_8a_cat_rows$`Pr(>|z|)`, method = "holm")

res_8b <- lmer(log(rt) ~ 
                 stimulus_config +
                 block * category +
                 # block * comparison_type +
                 options_adjacent +
                 cumulative_correct_transition_views_z +
                 cumulative_base_node_views_z +
                 correct_transition_last_view_z +
                 correct_dest_community +
                 correct_dest_node_type +
                 left_is_correct +
                 # age_z +
                 # gender +
                 # handedness +
                 # session_duration_z +
                 (1|participant_id),
               data = testing_rescaled
)
summary(res_8b)

res_8b2 <- lmer(log(rt) ~ block + cumulative_correct_transition_views_z +
                  cumulative_question_views_z +
                  (1|participant_id),
                data = testing_rescaled)
summary(res_8b2)
car::vif(res_8b2) # colinearity is not an issue

# MODEL RECONCILING ALL RT FINDINGS
res_8b3 <- lmer(log(rt) ~ block + cumulative_correct_transition_views_z * primary_tag +
       cumulative_question_views_z + (1|participant_id), data = testing_rescaled)
summary(res_8b3)
# this looks like evidence for task familiarity: if the decline reflected structure learning, 
# exposure to a specific transition should matter, but itt doesnt. if it reflected item specific priming, 
# question repetition should matter, but it doesnt either. 
# what's left is generic practice (faster at reading the display, locating options, clicking) 

# cant run this for category and comparison type at the same time, but different runs give different insights

res_8b_coefs <- as.data.frame(summary(res_8b)$coefficients)
res_8b_cat_rows <- res_8b_coefs
res_8b_cat_rows$p_adj_holm <- p.adjust(res_8b_cat_rows$`Pr(>|t|)`, method = "holm")

res_8c <- lmer(mean_confidence ~
                 stimulus_config +
                 # block * category + 
                 block * comparison_type +
                 options_adjacent +
                 # cumulative_correct_transition_views_z +
                 cumulative_base_node_views_z +
                 # correct_transition_last_view_z +
                 # correct_dest_community +
                 # correct_dest_node_type + 
                 # left_is_correct +
                 confidence_slider_start +
                 # age_z +
                 # gender +
                 # handedness +
                 session_duration_z +
                 (1|participant_id),
               data = all_confidence_omnibus
                 )
summary(res_8c)

res_8c_coefs <- as.data.frame(summary(res_8c)$coefficients)
res_8c_cat_rows <- res_8c_coefs
res_8c_cat_rows$p_adj_holm <- p.adjust(res_8c_cat_rows$`Pr(>|t|)`, method = "holm")

res_8d <- lmer(confdiff ~ 
                 stimulus_config +
                 # block * category +
                 # options_adjacent +
                 cumulative_correct_transition_views_z +
                 cumulative_base_node_views_z +
                 # correct_transition_last_view_z +
                 # correct_dest_community +
                 # correct_dest_node_type +
                 # left_is_correct +
                 confidence_slider_start +
                 # age_z +
                 # gender +
                 # handedness +
                 # session_duration_z +
                 (1|participant_id),
               data = all_confdiff_omnibus
)
# this doesn't make sense, too granular and too many na's. let's leave it at confidence for now


# ANALYSIS 9: 
testing_tags_regrouped <- testing %>%
  mutate(
    primary_tag = case_when(
      primary_tag == "symmetry_perception" ~ "other",
      primary_tag == "reaction_time" ~ "other",
      TRUE ~ primary_tag
    )
  ) %>%
  mutate(
    primary_tag = factor(primary_tag, levels = c("no_guess", "generic_pattern", "relational_transition", "memory", "other"))
  )
# regrouped because N was too small for some tags (criterion was, if N<5, add to "other")

comments_confidence_awareness <- testing_tags_regrouped %>%
  group_by(participant_id, block, noticed_arrangement) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE) / 100,
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE) / 100,
    confdiff = mean_confidence_correct - mean_confidence_incorrect,
    block_avg_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
  )

comments_confdiff_awareness <- comments_confidence_awareness %>%
  filter(!is.na(confdiff))

comments_confidence_tags <- testing_tags_regrouped %>%
  group_by(participant_id, block, primary_tag) %>%
  summarise(
    mean_confidence = mean(confidence_response, na.rm = TRUE) / 100,
    mean_confidence_correct = mean(confidence_response[correct == 1], na.rm = TRUE),
    mean_confidence_incorrect = mean(confidence_response[correct == 0], na.rm = TRUE),
    confdiff = (mean_confidence_correct - mean_confidence_incorrect) / 100,
    block_avg_rt = mean(rt, na.rm = TRUE),
    .groups = "drop"
  )

comments_confdiff_tags <- comments_confidence_tags %>%
  filter(!is.na(confdiff))

# first with explicit awareness claim
res_9a <- glmer(correct ~ block * noticed_arrangement + (1|participant_id), data = t1_testing, family = binomial)
summary(res_9a)

res_9b <- lmer(log(rt) ~ block * noticed_arrangement + (1|participant_id), data = testing)
summary(res_9b)

res_9c <- lmer(mean_confidence ~ block * noticed_arrangement + (1|participant_id), data = comments_confidence_awareness)
summary(res_9c)

res_9d <- lmer(confdiff ~ block * noticed_arrangement + (1|participant_id), data = comments_confdiff_awareness)
summary(res_9d)

# now with tags
res_9e <- glmer(correct ~ block * primary_tag + (1|participant_id), data = testing_tags_regrouped, family = binomial)
summary(res_9e)

res_9f <- lmer(log(rt) ~ block * primary_tag + (1|participant_id), data = testing_tags_regrouped)
summary(res_9f)

res_9g <- lmer(mean_confidence ~ block * primary_tag + (1|participant_id), data = comments_confidence_tags)
summary(res_9g)

res_9h <- lmer(confdiff ~ block * primary_tag + (1|participant_id), data = comments_confdiff_tags)
summary(res_9h)

# quick check for tags vs no tags
testing_tags_regrouped2 <- testing_tags_regrouped %>%
  mutate(
    has_tags = case_when(
      primary_tag %in% c("generic_pattern", "relational_transition", "memory", "other") ~ TRUE,
      TRUE ~ FALSE
    )
  )

# thsi is the global model grouping all tags, for the claim that commenters were faster
res_9i <- lmer(log(rt) ~ block * has_tags + (1|participant_id), data = testing_tags_regrouped2)
summary(res_9i)

# getting values of models for summary table in writeup
exp(fixef(res_9f)["(Intercept)"])
exp(fixef(res_9f)["block:primary_taggeneric_pattern"])

et <- emtrends(res_9f, ~ primary_tag, var = "block")
s  <- summary(et, infer = TRUE) # to get CIs
data.frame(
  tag = s$primary_tag,
  pct = (exp(s$block.trend) - 1) * 100,
  lower = (exp(s$asymp.LCL %||% s$lower.CL) - 1) * 100,
  upper = (exp(s$asymp.UCL %||% s$upper.CL) - 1) * 100
)
emtrends(res_9g, ~ primary_tag, var = "block", infer = TRUE)
emtrends(res_9h, ~ primary_tag, var = "block", infer = TRUE)

# counting how many participants reported knowledge
testing %>% 
  group_by(participant_id) %>% 
  summarise(
    noticed_arrangement = unique(noticed_arrangement), 
    task_purpose_awareness = unique(task_purpose_awareness)
    ) %>% count(noticed_arrangement)

testing %>% 
  group_by(participant_id) %>% 
  summarise(
    noticed_arrangement = unique(noticed_arrangement), 
    task_purpose_awareness = unique(task_purpose_awareness)
  ) %>% count(task_purpose_awareness)

comments %>%
  count(primary_tag)

# seeing if noticed_arragement = yes had better accuracy, given they had an interaction with confdiff
testing %>% group_by(participant_id, block, noticed_arrangement) %>% 
  summarise(mean_accuracy = sum(correct == 1, na.rm = TRUE) / n()) %>%
  group_by(noticed_arrangement, block) %>%
  summarise(mean_accuracy = mean(mean_accuracy, na.rm = TRUE))

# does the "aware gro"noticed_arragnement=yes" group differ from chance at the beginning?
m_aware <- glmer(correct ~ block + (1|participant_id),
                 data = filter(t1_testing, noticed_arrangement == "yes"),
                 family = binomial)
summary(m_aware)

# ANALYSIS 10: random walk descriptive analysis
learning %>% count(participant_id, block, node) %>% filter(n < 3)
# no node had less than 3 reps per block. some had 3. also see stats summary below

node_visits <- learning %>%
  count(participant_id, block, node) %>%
  complete(participant_id, block, node, fill = list(n = 0)) %>%
  group_by(block, node) %>%
  summarise(mean_visits = mean(n), sd = sd(n), median = median(n), min = min(n), max = max(n), .groups = "drop")

ggplot(node_visits, aes(x = node, y = mean_visits, fill = factor(block))) +
  geom_col(position = "dodge") +
  geom_errorbar(aes(ymin = mean_visits - sd, ymax = mean_visits + sd),
                position = position_dodge(width = 0.9), width = 0.2) +
  labs(x = "Node", y = "Mean visits per participant", fill = "Block") +
  theme_minimal()

# check that no walk was the same
learning %>% 
  arrange(participant_id, block, step) %>%
  group_by(participant_id) %>%
  summarise(
    walk = paste(node, collapse = ','), 
    ) %>%
  summarise(n_walks = n_distinct(walk))


# ANALISYS 11: RT by transition type on learning phase

learning_2 <- learning %>%
  arrange(participant_id, block, step) %>%
  group_by(participant_id, block) %>%
  mutate(
    community= if_else(node %in% c("A","B","C","D"), 1L, 2L),
    prev_community = lag(community),
    is_cross_transition = community != prev_community,
    block
  ) %>%
  ungroup()

res_11a <- lmer(log(cover_rt) ~ block * is_cross_transition + (1|participant_id), data = learning_2)
summary(res_11a)


### RANDOM GRAPHS
r1_testing <- t1_testing %>% 
  filter(category == 8) %>% 
  group_by(participant_id, block) %>%
  summarise(
    participant_accuracy = mean(correct, na.rm = TRUE),
    participant_rt = mean(rt, na.rm = TRUE),
    .groups = "drop") 
r1_testing_block <- t1_testing %>% 
  filter(category == 8) %>%
  group_by(participant_id, block) %>%
  summarise(
    participant_accuracy = mean(correct, na.rm = TRUE),
    participant_rt = mean(rt, na.rm = TRUE),
    .groups = "drop") %>%
  group_by(block) %>%
  summarise(
    mean_accuracy = mean(participant_accuracy),
    se_acc = sd(participant_accuracy) / sqrt(n()),
    mean_rt = mean(participant_rt),
    .groups = "drop"
  )


plot_r1 <- ggplot() +
  geom_boxplot(
    data = r1_testing,
    aes(x = factor(block), y = participant_accuracy),
    fill = "gray85",
    color = "gray50",
    width = 0.5,
    outlier.shape = NA
  ) +
  geom_line(
    data = r1_testing_block,
    aes(x = factor(block), y = mean_accuracy, group = 1),
    color = "black",
    linewidth = 1.2
  ) +
  geom_point(
    data = r1_testing_block,
    aes(x = factor(block), y = mean_accuracy),
    color = "black",
    size = 2.5
  ) +
  scale_x_discrete(labels = 1:4) +
  labs(y = "Accuracy", x = "Block") +
  theme_minimal()



q <- read.csv("data/2afc_question_candidates_v3.csv")
subset(q, comparison_pair_tag == "B1XB__B2WB" & base %in% c("B","D"))

