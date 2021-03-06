import React, { useEffect, useState } from "react";
import "../style/lineCard.css";
import axios from 'axios';
import FreqChart from "./freqChart";
import TransportImage from "./transportImage";

function LineCard({line, station}){
	const [gif, updateGif] = useState();
	const [statPanel, updateStatPanel] = useState(false);

	function click() {
		if (station.network === "Rennes"){
			if(statPanel == true) {
				updateStatPanel(false); 
			}
			else {
				updateStatPanel(true);
			}
		}
	}

	const fetchGif = () => {
		axios
		.get('https://moov-api.herokuapp.com/api/transport/getgif/')
		.then(response => {
			updateGif("data:gif/gif;base64,"+response.data.ctx.gif)
		})
	};

	useEffect(() => {
		fetchGif();
	})

	useEffect(() => {
		updateStatPanel(false);
	}, [line, station])

	return (
		<>
			<div className="result-text-wrapper" onClick={e => click()}>
				<div className="one" >
					<TransportImage transport={line.line} network={station.network} width={"30px"} height={"30px"} top={"50%"} webkitTransform={"translate(0%, 50%)"}></TransportImage>
				</div>
				<div className="two">
					<span className="direction">{line.destination}</span>
				</div>
				<img className="gif" src={gif} style={{float:"left"}}></img>
				<div className="three">
					<ul className="horaires">
						<li className="premierHoraire">{line.next_departures[0]}</li>
						<li className="deuxiemeHoraire">{line.next_departures[1]}</li>
						<li className="troisiemeHoraire">{line.next_departures[2]}</li>
					</ul>
				</div>
			</div>
			<div style={{height:"10px"}}></div>
			{statPanel && 
					<div className="statPanel">
						<div className="premiereStat">
							<h5>Fréquentation de la ligne</h5>
							<FreqChart station={station} line={line.line} />
						</div>
					</div>
			}
		</>

		)
}

export default LineCard;