# Written by Emile Delmas, Paul O'Reilly & Daya Lokesh Duddupudi
class WindTurbineCalculator:
    def __init__(self):
        # Siewind SWT-6.0-154 specifications
        self.rated_power = 6000.0  # Rated power in kW
        self.cut_in_speed = 4.0    # Cut-in wind speed in m/s
        self.rated_speed = 13.0    # Rated wind speed in m/s
        self.cut_out_speed = 25.0  # Cut-out wind speed in m/s
        self.hub_height = 135      # Hub height in meters (site specific - estimated)

    def calculate_air_density(self, temperature_celsius, pressure_pascal):
        """Calculate air density using temperature and pressure"""
        R = 287.05  # Specific gas constant for dry air, J/(kg·K)
        temperature_kelvin = temperature_celsius + 273.15
        density = pressure_pascal / (R * temperature_kelvin)
        return density

    def power_curve(self, wind_speed):
        """ turbine power curve function"""
        # Source : https://windpowerplus.com/wind-turbine-power-curve/
        if wind_speed < self.cut_in_speed:
            return 0.0
        elif wind_speed < 5.0:
            # Linear increase between cut-in speed and 5 m/s
            return self.rated_power * 0.2 * (wind_speed - self.cut_in_speed) / (5.0 - self.cut_in_speed)
        elif wind_speed < 10.0:
            # Quadratic increase between 5 m/s and 10 m/s
            fraction = (wind_speed - 5.0) / (10.0 - 5.0)
            return self.rated_power * (0.2 + 0.6 * fraction ** 2)
        elif wind_speed < self.rated_speed:
            # Near linear increase to rated power
            return self.rated_power * (0.8 + 0.2 * (wind_speed - 10.0) / (self.rated_speed - 10.0))
        elif wind_speed <= self.cut_out_speed:
            # Rated power between rated speed and cut-out speed
            return self.rated_power
        else:
            return 0.0

    def estimate_power_output(self, wind_speed, temperature_celsius, pressure_pascal):
        """
        Estimate power output based on wind speed and air conditions
        wind_speed: in m/s
        temperature_celsius: in °C
        pressure_pascal: in Pa
        Returns power in kW
        """
        if wind_speed < self.cut_in_speed or wind_speed > self.cut_out_speed:
            return 0.0

        # Calculate air density
        air_density = self.calculate_air_density(temperature_celsius, pressure_pascal)
        air_density_ratio = air_density / 1.225  # Ratio to standard air density

        # Get power output from the power curve
        power = self.power_curve(wind_speed)

        # convert from mechanical power to electrical power
        power = power * 0.95

        # Adjust power for air density
        return power * air_density_ratio
