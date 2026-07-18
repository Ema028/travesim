'''Derivado do código de cliente exemplo no repositório: https://github.com/futebol-mini/VSSClient.py'''
import socket
import math

from threading import Thread
from vssproto.simulation.command_pb2 import Command, Commands
from vssproto.simulation.common_pb2 import Frame
from vssproto.simulation.packet_pb2 import Environment, Packet

MAX_VEL = 10

def drive_to(robot, target_x, target_y):
    dx = target_x - robot.x
    dy = target_y - robot.y

    dist = math.sqrt(dx**2 + dy**2)
    angle= math.atan2(dy, dx) 
    error= angle - robot.orientation

    kp_angle = 2
    kp_dist  = 3
    
    vel  = kp_dist*dist
    kerro= kp_angle*error
    left = max(-MAX_VEL, min(MAX_VEL, vel-kerro))
    right= max(-MAX_VEL, min(MAX_VEL, vel+kerro))
    return left, right

def goalie_command(frame: Frame, yellowteam: bool) -> tuple[float, float]:  # noqa: ARG001, FBT001
    ball = frame.ball
    robot = frame.robots_yellow[0] if yellowteam else frame.robots_blue[0]

    goal_x = 0.70 if yellowteam else -0.70
    return drive_to(robot, goal_x, ball.y)


def defender_command(frame: Frame, yellowteam: bool) -> tuple[float, float]:  # noqa: ARG001, FBT001
    ball = frame.ball
    robot = frame.robots_yellow[1] if yellowteam else frame.robots_blue[1]

    goal_x = 0.70 if yellowteam else -0.70
    target_x = (goal_x + ball.x) / 2
    return drive_to(robot, target_x, ball.y)


def attacker_command(frame: Frame, yellowteam: bool) -> tuple[float, float]:  # noqa: ARG001, FBT001
    ball = frame.ball
    robot = frame.robots_yellow[2] if yellowteam else frame.robots_blue[2]

    dx = ball.x - robot.x
    dy = ball.y - robot.y
    dist = math.sqrt(dx*dx + dy*dy)

    if dist > 0.1:  return drive_to(robot, ball.x, ball.y)
    else:           return MAX_VEL,MAX_VEL


def main(yellow_team: bool) -> None:  # noqa: FBT001
    ###################################################################################
    # Connection setup
    ###################################################################################

    sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_in.bind(("224.0.0.1", 10002))
    sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if yellow_team: sock_out.connect(("127.0.0.1", 20012))
    else:           sock_out.connect(("127.0.0.1", 20013))
    
    ###################################################################################
    # Loop start
    ###################################################################################

    print("Loop start")

    try:
        while True:
            ###########################################################################
            # Receive data from simulator
            ###########################################################################

            data, address = sock_in.recvfrom(1024)
            print(f"Received {len(data)} bytes from {address}")

            environment_data = Environment()
            environment_data.ParseFromString(data)
            frame = environment_data.frame

            ###########################################################################
            # Process data from simulator
            ###########################################################################

            goalie_left_wheel, goalie_right_wheel = goalie_command(
                environment_data.frame,
                yellowteam=yellow_team,
            )

            defender_left_wheel, defender_right_wheel = defender_command(
                environment_data.frame,
                yellowteam=yellow_team,
            )

            attacker_left_wheel, attacker_right_wheel = attacker_command(
                environment_data.frame,
                yellowteam=yellow_team,
            )

            ###########################################################################
            # Send commands to simulator
            ###########################################################################

            cmd_packet = Commands()
            cmd_packet.robot_commands.append(
                Command(
                    id=0,
                    yellowteam=yellow_team,
                    wheel_left=goalie_left_wheel,
                    wheel_right=goalie_right_wheel,
                ),
            )

            cmd_packet.robot_commands.append(
                Command(
                    id=1,
                    yellowteam=yellow_team,
                    wheel_left=defender_left_wheel,
                    wheel_right=defender_right_wheel,
                ),
            )

            cmd_packet.robot_commands.append(
                Command(
                    id=2,
                    yellowteam=yellow_team,
                    wheel_left=attacker_left_wheel,
                    wheel_right=attacker_right_wheel,
                ),
            )

            packet = Packet()
            packet.cmd.CopyFrom(cmd_packet)

            sock_out.send(packet.SerializeToString())

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock_out.close()
        sock_in.close()

if __name__ == "__main__":
    yellow = Thread(target=main, args=(True,))
    blue   = Thread(target=main, args=(False,))

    yellow.start()
    blue.start()
