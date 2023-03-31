# -*- coding: utf-8 -*-
#
#  generate.py
#
#  Copyright 2023 KP
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import gc
from pathlib import Path

import cv2
import streamlit as st
import torch
from diffusers import DiffusionPipeline


# Adapted from: https://github.com/huggingface/diffusers/blob/main/src/diffusers/utils/testing_utils.py
def convert_to_video(video_frames: list, fps: int, filename: str) -> str:
    """Convert from numpy array of frame to webm"""
    Path("./outputs").mkdir(parents=True, exist_ok=True)
    output_video_path = f"./outputs/{filename}.webm"

    fourcc = cv2.VideoWriter_fourcc(*"VP90")
    h, w, c = video_frames[0].shape
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps=fps, frameSize=(w, h))

    for i in range(len(video_frames)):
        img = cv2.cvtColor(video_frames[i], cv2.COLOR_RGB2BGR)
        video_writer.write(img)

    return output_video_path


@st.cache_resource
def make_pipeline_generator(
    device: str, cpu_offload: bool, attention_slice: bool
) -> DiffusionPipeline:
    """Create text2video pipeline"""
    pipeline = DiffusionPipeline.from_pretrained(
        "damo-vilab/text-to-video-ms-1.7b",
        variant="fp16",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    )
    pipeline = pipeline.to(torch.device(device))
    if cpu_offload:
        pipeline.enable_sequential_cpu_offload()
    if attention_slice:
        pipeline.enable_attention_slicing()
    return pipeline


def generate(
    prompt: str,
    num_frames: int,
    num_steps: int,
    seed: int,
    height: int,
    width: int,
    cpu_offload: bool,
    attention_slice: bool,
) -> list:
    """Generate video with text2video pipeline"""
    # Get device
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    # Run model
    pipeline = make_pipeline_generator(
        device=device, cpu_offload=cpu_offload, attention_slice=attention_slice
    )
    generator = torch.Generator(device=torch.device(device)).manual_seed(seed)
    video = pipeline(
        prompt=prompt,
        num_frames=num_frames,
        num_inference_steps=num_steps,
        height=height,
        width=width,
        generator=generator,
    ).frames

    # Clean up memory
    torch.cuda.empty_cache()
    gc.collect()

    return video