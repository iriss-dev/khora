//! # KHORA-CORE
//!
//! Deterministic spatial kinematics, DCRA optical ray simulation,
//! and 40 kHz ultrasonic radiation pressure beamforming.
//!
//! Compatible with `#![no_std]` bare-metal microcontroller environments.

#![cfg_attr(not(feature = "std"), no_std)]

pub mod kinematics;
pub mod optics;
pub mod haptics;

pub use kinematics::SE3Transform;
pub use optics::DCRASubstrate;
pub use haptics::AcousticPhasedArray;
