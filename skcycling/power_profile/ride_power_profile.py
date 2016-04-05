""" Ride Power-Profile class.
"""

import warnings
import numpy as np
import copy_reg
import types

from joblib import Parallel, delayed

from .base_power_profile import BasePowerProfile

from ..utils import check_filename_fit
from ..utils import check_X
from ..utils import load_power_from_fit


def _rpp_parallel(X, idx_t_rpp):
    """ Function to compute the rpp in parallel

    Parameters
    ----------
    X : ndarray, shape (n_samples)
        The power records.

    idx_t_rpp : int
        Index of the time to compute the rpp.

    Return
    ------
    power : float
        Returns the best power for the given duration of the rpp.
    """
    # Slice the data such that we can compute efficiently the mean later
    t_crop = np.array([X[i:-idx_t_rpp + i:]
                       for i in range(idx_t_rpp)])
    # Check that there is some value cropped. In the case that
    # the duration is longer than the file, the table crop is
    # empty
    if t_crop.size is not 0:
        # Compute the mean for each of these samples
        t_crop_mean = np.mean(t_crop, axis=0)
        # Keep the best to store as rpp
        return np.max(t_crop_mean)
    else:
        return 0


class RidePowerProfile(BasePowerProfile):
    """ Class to handle the power-profile for one ride.

    Parameters
    ----------
    max_duration_profile : int or None
        Integer representing the maximum duration in minutes to build the
        record power-profile model. It can be infered if the data are loaded
        from a npy file.

    cyclist_weight : float, default None
        Float in order to normalise the record power-profile depending
        of its weight. By default this is None in order to avoid
        using the data from normalized rpp without this data.

    Attributes
    ----------
    data_ : array-like, shape (60 * max_duration_rpp, )
        Array in which the record power-profile is stored.
        The units used is the second.

    data_norm_ : array-like, shape (60 * max_duration_rpp, )
        Array in which the weight-normalized record power-profile
        is stored. The units used is the seconds.

    max_duration_data_ : int
        The maximum duration of the record power-profile.

    cyclist_weight_ : float
        Cyclist weight.

    filename_ : str
        The corresponding fit file attached to this power-profile.

    date_profile_ : date
        Date of the current power-profile.
    """

    def __init__(self, max_duration_profile=None, cyclist_weight=None):
        # Call the constructor of the parent class
        super(RidePowerProfile, self).__init__(max_duration_profile,
                                               cyclist_weight)

    def fit(self, filename):
        """ Read and build the power-profile from the fit file.

        Parameters
        ----------
        filename : str
            The corresponding fit file from which the power-profile will be
            extracted from.

        Return
        ------
        self : object
            Returns self.
        """
        self.filename_ = check_filename_fit(filename)

        # Open the fit file and get the data power and the associated date
        ride_power, self.date_profile_ = load_power_from_fit(self.filename_)

        # Compute the ride power profile
        # Check that the power data are ok
        ride_power = check_X(ride_power)

        # Compute the rpp in parallel
        # Check that the maximum duration of the profile was given
        if self.max_duration_profile_ is None:
            raise ValueError('You need to specify the maximum duration that is'
                             ' required during the profile computation.')
        # Make the processing with all the available processor
        pp = Parallel(n_jobs=-1)(delayed(_rpp_parallel)(ride_power,
                                                        idx_t_rpp)
                                 for idx_t_rpp
                                 in range(60 * self.max_duration_profile_))
        self.data_ = np.array(pp)
        # Compute the normalized rpp if we should
        if self.cyclist_weight_ is not None:
            self.data_norm_ = self.data_ / self.cyclist_weight_
        else:
            self.data_norm_ = None

        return self