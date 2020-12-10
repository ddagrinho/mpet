"""
This module provides functions defining properties of the ion-conducting
phase -- the electrolyte Manage functions for the parameters involved in
Stefan-Maxwell based concentrated electrolyte transport theory for
binary electrolytes.

Each electrolyte set must output functions for the following as a
function of c (electrolyte concentration, M)
 - Dchem [m^2/s] = the prefactor for grad(c) in species conservation
 - sigma [S/m] = the conductivity
 - (1 + dln(f_\pm)/dln(c)) = the "thermodynamic factor"
 - t_+^0 = the transference number of the cations
"""

import numpy as np

cref = 1.  # M
Tref = 298.  # K
N_A = 6.022e23
k = 1.381e-23
e = 1.602e-19


def LiClO4_PC():
    """ Set of parameters from Fuller, Doyle, Newman 1994, with
    conductivity directly from dualfoil5.2.f
    """
    def tp0(c):
        return 0.2

    def D(c):
        return 2.58e-10  # m^2/s

    def therm_fac(c):
        return 1.

    def sigma(cin):
        c = cin * 1000  # mol/m^3
        p_max = 0.542
        p_u = 0.6616
        a = 0.855
        b = -0.08
        rho = 1.2041e3
        out = 0.0001 + c**a * (
            p_max*(1./(rho*p_u))**a
            * np.exp(b*(c/rho - p_u)**2
                     - (a/p_u)*(c/rho - p_u)))  # S/m
        return out
    Dref = D(cref)

    def D_ndim(c):
        return D(c) / Dref

    def sigma_ndim(c):
        return sigma(c) * (
            k*Tref/(e**2*Dref*N_A*(1000*cref)))
    return D_ndim, sigma_ndim, therm_fac, tp0, Dref


def valoen_reimers():
    """ Set of parameters from Valoen and Reimers 2005 """
    def tp0(c):
        return 0.38

    def D(c):
        return (
            10**(-4) * 10**(-4.43 - 54/(Tref - (229 + 5*c)) - 0.22*c))  # m^2/s

    def therm_fac(c):
        tmp = 0.601 - 0.24*c**(0.5) + 0.982*(1 - 0.0052*(Tref - 294))*c**(1.5)
        return tmp/(1-tp0(c))

    def sigma(c):
        (k00, k01, k02,
         k10, k11, k12,
         k20, k21) = (
             -10.5, 0.0740, -6.96e-5,
             0.668, -0.0178, 2.80e-5,
             0.494, -8.86e-4)
        out = c * (k00 + k01*Tref + k02*Tref**2
                   + k10*c + k11*c*Tref + k12*c*Tref**2
                   + k20*c**2 + k21*c**2*Tref)**2  # mS/cm
        out *= 0.1  # S/m
        return out
    Dref = D(cref)

    def D_ndim(c):
        return D(c) / Dref

    def sigma_ndim(c):
        return sigma(c) * (
            k*Tref/(e**2*Dref*N_A*(1000*cref)))
    return D_ndim, sigma_ndim, therm_fac, tp0, Dref


def valoen_bernardi():
    """ Set of parameters from Bernardi and Go 2011, indirectly from
    Valoen and Reimers 2005. The only change from Valoen and Reimers
    is the conductivity.
    """
    D_ndim, Ign, therm_fac, tp0, Dref = valoen_reimers()

    def sigma(c):
        (k00, k01, k02,
         k10, k11, k12,
         k20, k21) = (
            -8.2488, 0.053248, -0.000029871,
            0.26235, -0.0093063, 0.000008069,
            0.22002, -0.0001765)
        out = c * (k00 + k01*Tref + k02*Tref**2
                   + k10*c + k11*c*Tref + k12*c*Tref**2
                   + k20*c**2 + k21*c**2*Tref)**2  # mS/cm
        out *= 0.1  # S/m
        return out

    def sigma_ndim(c):
        return sigma(c) * (
            k*Tref/(e**2*Dref*N_A*(1000*cref)))
    return D_ndim, sigma_ndim, therm_fac, tp0, Dref


def test1():
    """Set of dilute solution parameters with zp=|zm|=nup=num=1,
    Dp = 2.2e-10 m^2/s
    Dm = 2.94e-10 m^2/s
    """
    Dp = 2.2e-10
    Dm = 2.94e-10

    def D(c):
        return (2*Dp*Dm/(Dp+Dm))  # m^2/s

    def therm_fac(c):
        return 1.

    def tp0(c):
        return Dp/(Dp+Dm)

    def sigma(c):
        return Dm*(1000*c)*N_A*e**2/(k*Tref*(1-tp0(c)))  # S/m
    Dref = D(cref)

    def D_ndim(c):
        return D(c) / Dref

    def sigma_ndim(c):
        return sigma(c) * (
            k*Tref/(e**2*Dref*N_A*(1000*cref)))
    return D_ndim, sigma_ndim, therm_fac, tp0, Dref


def Colclasure20():
    def tp0(Ce):
        T=298
        Acoeff_Trfn = -0.0000002876102*T**2 + 0.0002077407*T - 0.03881203
        Bcoeff_Trfn = 0.000001161463*T**2 - 0.00086825*T + 0.1777266
        Ccoeff_Trfn = -0.0000006766258*T**2 + 0.0006389189*T + 0.3091761

        return (Acoeff_Trfn*Ce**2 + Bcoeff_Trfn*Ce
            + Ccoeff_Trfn)


    def D(Ce):
        T=298
        D_00 = -0.5688226
        D_01 = -1607.003
        D_10 = -0.8108721
        D_11 = 475.291
        D_20 = -0.005192312
        D_21 = -33.43827
        T_g0 = -24.83763
        T_g1 = 64.07366
        return(10**(D_00 + D_01 / (T - (T_g0 + T_g1 * Ce)) + (D_10 + D_11 / (T -
                            (T_g0 + T_g1 * Ce)))*Ce + (D_20 + D_21 / (T - (T_g0 + T_g1 * Ce)))*Ce**2)*0.0001)

    def therm_fac(c):
        T = 298
        return 1 + 0.341*np.exp(261/T)-0.00225*np.exp(1360/T)*c + 0.54*np.exp(329/T)*c**2

    def sigma(Ce):
        T=298
        Acoeff_Kappa = 0.0001909446*T**2 - 0.08038545*T + 9.00341
        Bcoeff_Kappa = -0.00000002887587*T**4 + 0.00003483638*T**3 - 0.01583677*T**2 + 3.195295*T - 241.4638
        Ccoeff_Kappa = 0.00000001653786*T**4 - 0.0000199876*T**3 + 0.009071155*T**2 - 1.828064*T + 138.0976
        Dcoeff_Kappa = -0.000000002791965*T**4 + 0.000003377143*T**3 - 0.001532707*T**2 + 0.3090003*T - 23.35671

        return (Ce * (Acoeff_Kappa + Bcoeff_Kappa * Ce
            + Ccoeff_Kappa * Ce**2 + Dcoeff_Kappa * Ce**3))

    Dref = D(cref)

    def D_ndim(c):
        return D(c) / Dref

    def sigma_ndim(c):
        return sigma(c) * (
            k*Tref/(e**2*Dref*N_A*(1000*cref)))
    
    return D_ndim, sigma_ndim, therm_fac, tp0, Dref
