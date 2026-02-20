package org.firstinspires.ftc.teamcode;

import static org.firstinspires.ftc.robotcore.external.BlocksOpModeCompanion.hardwareMap;

import com.qualcomm.hardware.rev.RevHubOrientationOnRobot;
import com.qualcomm.robotcore.eventloop.opmode.LinearOpMode;
import com.qualcomm.robotcore.eventloop.opmode.TeleOp;
import com.qualcomm.robotcore.hardware.DcMotor;
import com.qualcomm.robotcore.hardware.DcMotorEx;
import com.qualcomm.robotcore.hardware.DcMotorSimple;
import com.qualcomm.robotcore.hardware.IMU;
import com.qualcomm.robotcore.util.ElapsedTime;

import org.firstinspires.ftc.robotcore.external.navigation.AngleUnit;

@TeleOp(name = "bv_rob", group = "Main")
public class bv_rob extends LinearOpMode {
    DcMotor LeftFrontDrive, LeftRearDrive, RightFrontDrive, RightRearDrive;
    DcMotorEx Lift;
    IMU imu;
    private ElapsedTime timer = new ElapsedTime();
    double correctionFactor = 0.85;
    boolean aPrev = false, bPrev = false;
    double headingOffset = 0;
    double TICKS_PER_REV = 28;
    double MAX_RPM = 6000;
    double RUN_TIME_SECONDS = 0.9;

    double RUN_TIME_razg = 0.1;
    double PRM_low = 2050;
    double PRM_razg = -3700;
    double PRM_up = -3000;


    @Override
    public void runOpMode() {

        LeftFrontDrive = hardwareMap.get(DcMotor.class, "leftFront");
        LeftRearDrive = hardwareMap.get(DcMotor.class, "leftBack");
        RightFrontDrive = hardwareMap.get(DcMotor.class, "rightFront");
        RightRearDrive = hardwareMap.get(DcMotor.class, "rightBack");

        Lift =  hardwareMap.get(DcMotorEx.class, "lift");
        Lift.setMode(DcMotor.RunMode.STOP_AND_RESET_ENCODER);
        Lift.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);
        double maxVelocityTicksPerSec = (MAX_RPM * TICKS_PER_REV) / 60.0;

        //32767 - максимальное значение, которое может храниться в знаковом 16-битном целом числе = 100% мощности
        double kF = 32767.0 / maxVelocityTicksPerSec;

        double kP = 0.1 * kF;
        double kI = 0.01 * kP;
        double kD = 0.0;
        Lift.setVelocityPIDFCoefficients(kP, kI, kD, kF);
        Lift.setPositionPIDFCoefficients(5.0);
        Lift.setMode(DcMotor.RunMode.RUN_USING_ENCODER);
        double targetVelocity_up = (PRM_up * TICKS_PER_REV) / 60.0;
        double targetVelocity_low = (PRM_low * TICKS_PER_REV) / 60.0;
        double targetVelocity_up_razg =(PRM_razg * TICKS_PER_REV) / 60.0;
        RightFrontDrive.setDirection(DcMotor.Direction.REVERSE);
        RightRearDrive.setDirection(DcMotor.Direction.REVERSE);

        LeftFrontDrive.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);
        LeftRearDrive.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);
        RightFrontDrive.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);
        RightRearDrive.setZeroPowerBehavior(DcMotor.ZeroPowerBehavior.BRAKE);

        imu = hardwareMap.get(IMU.class, "imu");
        IMU.Parameters parameters = new IMU.Parameters(new RevHubOrientationOnRobot(
                RevHubOrientationOnRobot.LogoFacingDirection.RIGHT,
                RevHubOrientationOnRobot.UsbFacingDirection.FORWARD));
        imu.initialize(parameters);
        waitForStart();
        headingOffset = imu.getRobotYawPitchRollAngles().getYaw(AngleUnit.RADIANS);
        while (opModeIsActive()) {

            double heading = imu.getRobotYawPitchRollAngles().getYaw(AngleUnit.RADIANS) - headingOffset;
            if (gamepad1.x) {
                headingOffset = imu.getRobotYawPitchRollAngles().getYaw(AngleUnit.RADIANS);
            }

            if (gamepad1.dpad_right) correctionFactor = Math.min(1.0, correctionFactor + 0.02);
            if (gamepad1.dpad_left) correctionFactor = Math.max(0.5, correctionFactor - 0.02);

            double y = -gamepad1.left_stick_y;
            double x = -gamepad1.left_stick_x;
            double rot = -gamepad1.right_stick_x;

            if (Math.abs(y) < 0.05) y = 0;
            if (Math.abs(x) < 0.05) x = 0;
            if (Math.abs(rot) < 0.05) rot = 0;

            double cosA = Math.cos(heading);
            double sinA = Math.sin(heading);
            double fieldX = x * cosA - y * sinA;
            double fieldY = x * sinA + y * cosA;

            double lf = fieldY - fieldX + rot;
            double lb = fieldY + fieldX + rot;
            double rf = fieldY + fieldX - rot;
            double rb = fieldY - fieldX - rot;

            if (gamepad1.dpad_up) {
                lf = lb = rf = rb = 0.3;
            }
            if (gamepad1.dpad_down) {
                lf = lb = rf = rb = -0.3;
            }
            if (gamepad1.dpad_left) {
                lf = -0.4;
                lb = 0.4;
                rf = 0.4;
                rb = -0.4;
            }
            if (gamepad1.dpad_right) {
                lf = 0.4;
                lb = -0.4;
                rf = -0.4;
                rb = 0.4;
            }

            double max = Math.max(Math.abs(lf), Math.max(Math.abs(lb), Math.max(Math.abs(rf), Math.abs(rb))));
            if (max > 1.0) {
                lf /= max;
                lb /= max;
                rf /= max;
                rb /= max;
            }

            LeftFrontDrive.setPower(lf * 0.75);
            LeftRearDrive.setPower(lb * 0.75);
            RightFrontDrive.setPower(rf * 0.75);
            RightRearDrive.setPower(rb * 0.75);
            if (gamepad1.b && !bPrev) {
                timer.reset();
            }
            if (gamepad1.b){
                double elapsed = timer.seconds();
                if (elapsed < (RUN_TIME_SECONDS + 0.03)){
                    Lift.setVelocity(1100);
                } else{
                    Lift.setVelocity(0);
                }
            }
            bPrev = gamepad1.b;
            if (gamepad1.a && !aPrev) {
                timer.reset();
            }
            if (gamepad1.a) {
                double elapsed = timer.seconds();
                if (elapsed < RUN_TIME_razg) {
                    Lift.setVelocity(targetVelocity_up_razg * 20);
                } else if (elapsed < RUN_TIME_SECONDS) {
                    Lift.setVelocity(targetVelocity_up * 20);
                } else{
                    Lift.setPower(0);
                }
            }
            aPrev = gamepad1.a;
    }
}
}
