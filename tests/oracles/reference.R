args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(dirname(args[[1]]))
upstream <- normalizePath(args[[3]])
revision <- system2("git", c("-C", shQuote(upstream), "rev-parse", "HEAD"), stdout = TRUE)
stopifnot(revision == "1848df872cd6455a554ca737a608bc11f233d8a7")
Rcpp::sourceCpp(file.path(upstream, "src", "segment_simple.cpp"), cacheDir = file.path(root, "rcpp_cache"))
oracle_rc <- function(x) paste(rev(strsplit(chartr("ACGT", "TGCA", x), "")[[1]]), collapse = "")
for (name in c("seg_simple", "lcprefix_fast", "gen_83_type_string", "gen_89_type_mh_string", "gen_476_type_mh_string", "gen_89_type_string", "gen_476_type_string", "justify_indel", "catalog_row_order")) {
  source(file.path(upstream, "R", paste0(name, ".R")))
}
code <- readLines(file.path(upstream, "R", "categorize_1_justified_indel.R"))
eval(parse(text = gsub("fastrc::fast_rc", "oracle_rc", code, fixed = TRUE)))

classify <- function(context, position, ref, alt) {
  p <- as.integer(position)
  stopifnot(substr(context, p, p + nchar(ref) - 1) == ref)
  while (nchar(ref) && nchar(alt) && substr(ref, 1, 1) == substr(alt, 1, 1)) {
    ref <- substring(ref, 2); alt <- substring(alt, 2); p <- p + 1L
  }
  while (nchar(ref) && nchar(alt) && substr(ref, nchar(ref), nchar(ref)) == substr(alt, nchar(alt), nchar(alt))) {
    ref <- substr(ref, 1, nchar(ref) - 1); alt <- substr(alt, 1, nchar(alt) - 1)
  }
  if (nchar(ref) && nchar(alt)) {
    delta <- abs(nchar(ref) - nchar(alt))
    interval <- if (delta <= 1) "(0,1)" else if (delta <= 5) "(2,5)" else if (delta <= 10) "(6,10)" else if (delta <= 20) "(11,20)" else "(21,)"
    return(c("Complex", paste0("Complex", interval)))
  }
  op <- if (nchar(ref)) "d" else "i"
  word <- if (op == "d") ref else alt
  if (op == "d") {
    long <- context
    short <- paste0(substr(context, 1, p - 1), substring(context, p + nchar(word)))
  } else {
    short <- context
    long <- paste0(substr(context, 1, p - 1), word, substring(context, p))
  }
  justified <- justify_indel(long, short, p, expected_delta = word)
  result <- categorize_1_justified_indel(context, op, justified$del_str, justified$leftmost_pos)
  # The upstream per-event function retains one historical closed spelling;
  # catalog row ordering uses the equivalent open interval.
  result$Koh_89 <- sub("Del(C):R(6,9)", "Del(C):R(6,)", result$Koh_89, fixed = TRUE)
  c(result$Koh_89, result$Koh_476)
}
events <- read.delim(args[[1]], stringsAsFactors = FALSE)
answers <- lapply(seq_len(nrow(events)), function(i) {
  e <- events[i, ]
  tryCatch(classify(e$sequence, e$position, e$reference, e$alternate), error = function(err) c("ERROR", conditionMessage(err)))
})
events$id89 <- vapply(answers, `[`, character(1), 1)
events$id476 <- vapply(answers, `[`, character(1), 2)
write.table(events, args[[2]], sep = "\t", row.names = FALSE, quote = FALSE)
orders <- catalog_row_order()
writeLines(orders$ID89, file.path(root, "oracle_ID89_channels.txt"))
writeLines(orders$ID476, file.path(root, "oracle_ID476_channels.txt"))
