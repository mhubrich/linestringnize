# Linestringnize
This package transforms on-street points to block-wise linestrings. The constructed linestrings are parallel to the curvature of the road they lay on. To satisfy this condition, a road network is queried from OpenStreetMap. Points are grouped per street-block (separating left and right side of the block) by solving the travelling salesman problem.

## Examples
In both examples, on-street parking meter data was obtained from open government data. The parking meters are transformed to linestrings, which can be further used in GIS and mapping applications.
<table>
  <tr>
    <td>
      <figure>
          <img src="/examples/vancouver.png"
               alt="Points and generated lines in Vancouver">
          <figcaption>Original points (red) and generated lines (yellow) in Vancouver, Canada.</figcaption>
      </figure>
    </td>
    <td>
      <figure>
          <img src="/examples/sanfrancisco.png"
               alt="Points and generated lines in San Francisco">
          <figcaption>Original points (red) and generated lines (yellow) in San Francisco, USA.</figcaption>
      </figure>
    </td>
  </tr>
</table>

## Getting Started
To get a local copy simply clone this repository: `git clone https://github.com/mhubrich/linestringnize.git`

## Usage
To run the package, simply execute `python linestringnize.py` in the command line with the following (optional) arguments:
- `--input`: path to the input file
- `--output`: path to the output file
- `--id`: name of the feature ID property
- `--max_distance`: maximum distance between two points to be connected by a line
- `--min_length`: minimum length of a line
- `--clipping`: minimum buffer in meter between line start/end and intersection
- `--stats`: if true, output file contains statistics on the aggregations

## Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some amazing feature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgment
Shout-out to [@dmishin](https://github.com/dmishin) for providing the [tsp-solver](https://github.com/dmishin/tsp-solver) package, a sub-optimal travelling salesman problem (TSP) solver.

## Author
[Markus Hubrich](https://github.com/mhubrich)
