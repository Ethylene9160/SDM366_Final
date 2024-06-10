from __future__ import annotations

import random
import warnings

import cv2
import glfw
import mujoco
import numpy as np
from stable_baselines3 import PPO

import tools

warnings.filterwarnings("ignore")


def calculate_reward_fake(state_list):
    return 0


def init_glfw(width=1080, height=600):
    if not glfw.init():
        return None
    window = glfw.create_window(width, height, "MuJoCo Simulation", None, None)
    if not window:
        glfw.terminate()
        return None
    glfw.make_context_current(window)
    return window


def render(window, mujoco_model, mujoco_data):
    width, height = glfw.get_framebuffer_size(window)
    scene = mujoco.MjvScene(mujoco_model, maxgeom=1000)
    context = mujoco.MjrContext(mujoco_model, mujoco.mjtFontScale.mjFONTSCALE_150)

    mujoco.mjv_updateScene(mujoco_model, mujoco_data, mujoco.MjvOption(), None, mujoco.MjvCamera(),
                           mujoco.mjtCatBit.mjCAT_ALL, scene)
    mujoco.mjr_render(mujoco.MjrRect(0, 0, width, height), scene, context)

    buffer = np.zeros((height, width, 3), dtype=np.uint8)
    mujoco.mjr_readPixels(buffer, None, mujoco.MjrRect(0, 0, width, height), context)
    buffer = np.flipud(buffer)
    cv2.imshow("MuJoCo Simulation", buffer)
    cv2.waitKey(1)


def video_record(mujoco_model, mujoco_data, video_writer):
    width, height = glfw.get_framebuffer_size(window)
    scene = mujoco.MjvScene(mujoco_model, maxgeom=1000)
    context = mujoco.MjrContext(mujoco_model, mujoco.mjtFontScale.mjFONTSCALE_150)

    mujoco.mjv_updateScene(mujoco_model, mujoco_data, mujoco.MjvOption(), None, mujoco.MjvCamera(),
                           mujoco.mjtCatBit.mjCAT_ALL, scene)
    mujoco.mjr_render(mujoco.MjrRect(0, 0, width, height), scene, context)

    buffer = np.zeros((height, width, 3), dtype=np.uint8)
    mujoco.mjr_readPixels(buffer, None, mujoco.MjrRect(0, 0, width, height), context)
    buffer = np.flipud(buffer)

    if video_writer is not None:
        video_writer.write(buffer)


if __name__ == "__main__":
    xml_path = "Lifer_inverted_swing_pendulum.xml"
    model_path_a = "models_v4/a/temp_1718003498_epoch_5098.zip"
    model_path_b = "models_v4/b/temp_1718003498_epoch_5098.zip"
    model, data = tools.init_mujoco(xml_path)
    window = init_glfw()

    if_random_seed = 1
    seed = random.randint(0, 100000) if if_random_seed else 39858
    print(f'The seed is: {seed}')

    if window:
        try:
            obs_space_dims = 6
            action_space_dims = model.nu

            # Load PPO models
            env_a = tools.CustomEnv(model, data, calculate_reward_fake)
            env_b = tools.CustomEnv(model, data, calculate_reward_fake)
            agent_a = PPO.load(model_path_a, env=env_a)
            agent_b = PPO.load(model_path_b, env=env_b)

            total_num_episodes = int(10)
            time_records = []

            for episode in range(total_num_episodes):
                done = False
                data.time = 0
                print('The episode is:', episode)
                mujoco.mj_resetData(model, data)
                tools.random_state(data, seed)

                while not done:
                    state = tools.get_obs_lifer(data)
                    state_theta = np.arctan2(state[2], state[3])

                    x, theta, sin_theta, cos_theta, x_dot, theta_dot = state
                    if abs(x) < 0.55 and abs(theta) < 0.23 and abs(x_dot) < 0.8 and abs(theta_dot) < 0.8:
                        print('The state is:', state)

                    if abs(state_theta) < 0.23:
                        action, _ = agent_a.predict(state)
                    else:
                        action, _ = agent_b.predict(state)

                    data.ctrl[0] = action[0]  # Ensure action is correctly assigned
                    mujoco.mj_step(model, data)

                    done = data.time > 450  # Example condition to end episode

                    render(window, model, data)
                    # print(state_theta)

                time_records.append(data.time)
                print(f'lasted for {data.time:.2f} seconds')

        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            glfw.destroy_window(window)

        glfw.terminate()
