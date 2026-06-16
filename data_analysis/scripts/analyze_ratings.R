
library("tidyverse")
library("afex")
library("emmeans")

theme_set(
  theme_bw(base_size = 15) +
    theme(legend.position = "bottom")
)

ratings <- read_csv("../../test_experiment/results/ratings.csv")
glimpse(ratings)

# ── Means by stimulus (fractal × variant) ─────────────────────────────────────

means <- ratings |>
  group_by(stimulus_id, variant, stimulus) |>
  summarise(
    mean_rating = mean(rating, na.rm = TRUE),
    n           = n(),
    .groups     = "drop"
  ) |>
  arrange(stimulus_id, variant)

print(means, n = Inf)

# ── Helper: build one rating plot for a single variant ────────────────────────

plot_ratings <- function(data, means, v, colour, title) {
  data |>
    filter(variant == v) |>
    left_join(filter(means, variant == v), by = c("stimulus_id", "variant", "stimulus")) |>
    mutate(stimulus_id = fct_reorder(stimulus_id, mean_rating)) |>
    ggplot(aes(x = stimulus_id, y = rating)) +
    geom_jitter(
      colour = colour,
      width = 0.15, height = 0.15,
      alpha = 0.5, size = 2
    ) +
    geom_point(aes(y = mean_rating), size = 4, shape = 18) +
    scale_y_continuous(breaks = 1:5, limits = c(0.5, 5.5)) +
    labs(
      title    = title,
      subtitle = "Dots = individual ratings  ◆ = mean",
      x        = "Fractal",
      y        = "Rating (1 = not symmetrical, 5 = completely symmetrical)"
    ) +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
}

plot_A <- plot_ratings(ratings, means, "A", "#e67e22", "Asymmetrical stimuli (A) — ordered by mean rating")
plot_S <- plot_ratings(ratings, means, "S", "#2980b9", "Symmetrical stimuli (S) — ordered by mean rating")

print(plot_A)
print(plot_S)
