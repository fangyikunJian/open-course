#!/bin/bash
# 3Blue1Brown 讲解方法论语料。挑选标准：
#  (a) 元层面——他分析自己讲解得失的视频（最有价值）
#  (b) 硬概念的从零建构（卷积/中心极限/熵/Laplace）
#  (c) 长系列的开篇（要负责建立直觉地基）
cd "G:/open course/reinforcement learning/corpus/3b1b"
IDS=(
  Dlsa9EBKDGI   # Where my explanation of Grover's algorithm failed  ← 元分析，最关键
  _BrFKp-U8GI   # Exploration & Epiphany（讲「讲解」本身）
  l6DKRf-fAAM   # Reinventing Entropy
  GlYgs6v2YfU   # But what is cross-entropy?
  KuXjwB4LzSA   # But what is a convolution?
  zeJD6dqJ5lo   # But what is the Central Limit Theorem?
  IaSGqQa5O-M   # Convolutions | Why X+Y in probability
  d_qvLDhkg00   # Why Gaussian + Gaussian = Gaussian
  j0wJBEZdwLs   # But what is a Laplace Transform?
  eMlx5fFNoYc   # Attention in transformers, step-by-step
  wjZofJX0v4M   # Transformers, the tech behind LLMs
  LPZh9BOjkQs   # Large Language Models explained briefly
  6dTyOl1fmDo   # Why colliding blocks compute pi
  YtkIWDE36qU   # This pattern breaks, but for a good reason
  cy8r7WSuT1I   # Why pi is in the normal distribution
)
for id in "${IDS[@]}"; do
  [ -s "$id.en.vtt" ] && { echo "[skip] $id"; continue; }
  yt-dlp --skip-download --write-auto-subs --write-subs --sub-langs "en.*" \
         --sub-format vtt -o "$id" --sleep-requests 1 \
         "https://www.youtube.com/watch?v=$id" >/dev/null 2>&1 \
    && echo "[ ok ] $id" || echo "[FAIL] $id"
done
echo "--- 探测系列播放列表（不假设 ID，实际核验）---"
for pl in PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi; do
  n=$(yt-dlp --flat-playlist --print "%(title)s" "https://www.youtube.com/playlist?list=$pl" 2>/dev/null | wc -l)
  echo "$pl -> $n 个视频"
done
ls *.vtt 2>/dev/null | wc -l | sed 's/^/字幕文件数: /'
