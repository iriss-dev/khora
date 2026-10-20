//! SE(3) Rigid body transformations and S-Curve jerk-bounded trajectories.

#[cfg(not(feature = "std"))]
use core::ops::{Add, Sub, Mul};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Vector3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

impl Vector3 {
    pub const ZERO: Self = Self { x: 0.0, y: 0.0, z: 0.0 };

    pub fn new(x: f32, y: f32, z: f32) -> Self {
        Self { x, y, z }
    }

    pub fn dot(&self, other: &Self) -> f32 {
        self.x * other.x + self.y * other.y + self.z * other.z
    }

    pub fn cross(&self, other: &Self) -> Self {
        Self {
            x: self.y * other.z - self.z * other.y,
            y: self.z * other.x - self.x * other.z,
            z: self.x * other.y - self.y * other.x,
        }
    }

    pub fn norm_squared(&self) -> f32 {
        self.dot(self)
    }
}

/// 4x4 Homogeneous transformation matrix in SE(3).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SE3Transform {
    pub m: [[f32; 4]; 4],
}

impl SE3Transform {
    pub const IDENTITY: Self = Self {
        m: [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
    };

    pub fn from_translation(x: f32, y: f32, z: f32) -> Self {
        let mut t = Self::IDENTITY;
        t.m[0][3] = x;
        t.m[1][3] = y;
        t.m[2][3] = z;
        t
    }

    pub fn multiply(&self, other: &Self) -> Self {
        let mut res = [[0.0f32; 4]; 4];
        for i in 0..4 {
            for j in 0..4 {
                res[i][j] = self.m[i][0] * other.m[0][j]
                    + self.m[i][1] * other.m[1][j]
                    + self.m[i][2] * other.m[2][j]
                    + self.m[i][3] * other.m[3][j];
            }
        }
        Self { m: res }
    }

    /// Exact inverse for rigid body transform in SE(3): R^T and -R^T * t.
    pub fn inverse(&self) -> Self {
        let r_t = [
            [self.m[0][0], self.m[1][0], self.m[2][0]],
            [self.m[0][1], self.m[1][1], self.m[2][1]],
            [self.m[0][2], self.m[1][2], self.m[2][2]],
        ];
        let t = [self.m[0][3], self.m[1][3], self.m[2][3]];
        let inv_t = [
            -(r_t[0][0]*t[0] + r_t[0][1]*t[1] + r_t[0][2]*t[2]),
            -(r_t[1][0]*t[0] + r_t[1][1]*t[1] + r_t[1][2]*t[2]),
            -(r_t[2][0]*t[0] + r_t[2][1]*t[1] + r_t[2][2]*t[2]),
        ];
        Self {
            m: [
                [r_t[0][0], r_t[0][1], r_t[0][2], inv_t[0]],
                [r_t[1][0], r_t[1][1], r_t[1][2], inv_t[1]],
                [r_t[2][0], r_t[2][1], r_t[2][2], inv_t[2]],
                [0.0,       0.0,       0.0,       1.0],
            ],
        }
    }

    pub fn transform_point(&self, p: &Vector3) -> Vector3 {
        Vector3 {
            x: self.m[0][0]*p.x + self.m[0][1]*p.y + self.m[0][2]*p.z + self.m[0][3],
            y: self.m[1][0]*p.x + self.m[1][1]*p.y + self.m[1][2]*p.z + self.m[1][3],
            z: self.m[2][0]*p.x + self.m[2][1]*p.y + self.m[2][2]*p.z + self.m[2][3],
        }
    }

    pub fn transform_vector(&self, v: &Vector3) -> Vector3 {
        Vector3 {
            x: self.m[0][0]*v.x + self.m[0][1]*v.y + self.m[0][2]*v.z,
            y: self.m[1][0]*v.x + self.m[1][1]*v.y + self.m[1][2]*v.z,
            z: self.m[2][0]*v.x + self.m[2][1]*v.y + self.m[2][2]*v.z,
        }
    }

    pub fn translation(&self) -> Vector3 {
        Vector3::new(self.m[0][3], self.m[1][3], self.m[2][3])
    }
}
