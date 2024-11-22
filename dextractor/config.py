import yt
import yaml
from pathlib import Path
from unyt import unyt_quantity


class Config:
    """Config class that provides configuration options for pkg. Here one can set the loader, units, conversion tables
    etc. to be used.
    """
    _instance = None  # Class-level variable to hold the single instance

    def __new__(cls, *args, **kwargs):
        """Override the __new__ method to ensure only one instance."""
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_config()
        return cls._instance

    def _initialize_config(self):
        """Initialize the default configuration settings. It initializes the default snap loader and data parser
        (extract data with internal units, change to working units and save relevant simulation parameters such as
        cosmology, boxsize, particle numbers etc.) that may be overrun by custom user functions if whished, 
        base units of the simulation and the working units.
        The base units are not always used, e.g. when data is loaded with defaults, i.e. using the yt package, units
        are directly in place thanks to unyt.

        All attributes may be overrun by the user.

        List of attributes
        ------------------
        loader : func
            Loader of data
        parser : func
            Parser of data: extracts raw data, units, parameters, ...
        base_units : dict[str : str]
            Units of the simulation.
        working_units : dict[str : str]
            Units to work with.
        """
        self._package_dir = str(Path(__file__).resolve().parent)
        self.loader = Config.default_loader
        self.parser = Config.default_parser
        self.base_units = None
        self.fields = None
        self.working_units = {
            'dimensionless': 'dimensionless',
            'mass': "Msun",
            'time': "Gyr",
            'length': "kpc",
            'velocity': "km/s",
            'comoving': False
        }
        self.ptypes = None

        self._code = None

        self.ds = None

    @property
    def code(self):
        """Getter for the code attribute.
        """
        return self._code

    @code.setter
    def code(self, value):
        """Sets base_units, ptypes and fields according to yaml configuration files for each code type.
        """
        if self._code != value.upper():  # Only execute logic if the value changes
            self._code = value.upper()
            self._load_code_config()
        else:
            pass

    def _load_code_config(self):
        """Loads base_units, ptypes and their fields and gas type from the .yaml configuration file corresponding
        to the precise code. YAML files are stored in package-dir/CodeConfig

        Returns
        -------
        None
        """
        with open(self._package_dir + "/CodeConfig/" + self._code + ".yaml", 'r') as f:
            config_data = yaml.safe_load(f)

            self.base_units = config_data['base_units']
            self.ptypes = {
                'stars': config_data['stars']['pt'],
                'darkmatter': config_data['darkmatter']['pt'],
                'gas': config_data['gas']['pt'],
                'gas_type': config_data['gas_type']
            }
            self.fields = {
                'stars': config_data['stars']['fields'],
                'darkmatter': config_data['darkmatter']['fields'],
                'gas': config_data['gas']['fields']
            }

        return None

    @staticmethod
    def check_consistent_units(base_units, units):
        """Checks if base_units == units for consistency when loading and parsing data with yt and using CodeConfig files.
        Parameters
        ----------
        units : dict[str : str]
            Units to check agains units saved in self.base_units

        Returns
        -------
        None
        """
        if base_units is None:
            return None

        for key, unit in base_units.items():
            assert unit == unyt_quantity(1, units[key]), f"{key.upper(
            )} units do not coincide to 1E-10 precision. Units read from config file is {unit} but those read from yt are {units[key]}!"

    @staticmethod
    def default_loader(fn):
        """Default loader. Returns yt.dataset
        """
        ds = yt.load(fn)
        Config._instance.ds = ds
        return ds

    @staticmethod
    def default_parser(ds, center, radius):
        """Default parser: extracts data from selected region with working units, and gets relevant metadata
        """
        sp = ds.sphere(center, radius)

        units = {'time': Config.convert_unyt_quant_str(ds.time_unit),
                 'mass':  Config.convert_unyt_quant_str(ds.mass_unit),
                 'length': Config.convert_unyt_quant_str(ds.length_unit),
                 'velocity':  Config.convert_unyt_quant_str(ds.velocity_unit),
                 'comoving': str(ds.length_unit.units).split("/")[0].endswith("cm")
                 }

        metadata = {'redshift': ds.current_redshift,
                    'scale_factor': 1 / (ds.current_redshift + 1),
                    'time': ds.current_time,
                    'hubble_constant': ds.cosmology.hubble_constant,
                    'omega_matter': ds.cosmology.omega_matter,
                    'omega_lambda': ds.cosmology.omega_lambda,
                    'omega_radiation': ds.cosmology.omega_radiation,
                    'omega_curvature': ds.cosmology.omega_curvature,
                    'omega': ds.cosmology.omega_matter + ds.cosmology.omega_lambda +
                    ds.cosmology.omega_radiation + ds.cosmology.omega_curvature
                    }

        return units, metadata, sp

    @staticmethod
    def convert_unyt_quant_str(un):
        """Converts a unyt_quantity into a string of format value * unit, taking into account that
        unit may be composite.

        Parameters
        ----------
        un : unyt_quantity
            Quantity to be converted

        Returns
        -------
        u : str
        """
        un_bits = str(un.units).strip().split("*")
        try:
            f = float(un_bits[0])
            u = f"{(un.value * f):.10e} * {'*'.join(un_bits[1:])}"
        except:
            u = f"{un.value:.10e} * {'*'.join(un_bits[:])}"

        return u


config = Config()
