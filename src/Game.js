import React from 'react';
import './Game.scss';

class Square extends React.Component {
  render () {
    return (
      <button
        className="square"
        onClick={this.props.onClick}>
          {this.props.value}
      </button>
    );
  }
}

class Board extends React.Component {
  constructSquare(i) {
    return (
      <Square
        value={this.props.squares[i]}
        onClick={() => this.props.onClick(i)}
      />
    );
  }

  render() {
    let move = this.props.isXTurn ? 'X' : 'O';
    return (
      <div id="board">
        Next Move: {move}
        <div className="board-row">
          {this.constructSquare(0)}
          {this.constructSquare(1)}
          {this.constructSquare(2)}
        </div>
        <div className="board-row">
          {this.constructSquare(3)}
          {this.constructSquare(4)}
          {this.constructSquare(5)}
        </div>
        <div className="board-row">
          {this.constructSquare(6)}
          {this.constructSquare(7)}
          {this.constructSquare(8)}
        </div>
      </div>
    );
  }
}

class Game extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      squares: Array(9).fill(null),
      isXTurn: true,
      XWins: 0,
      OWins: 0,
    }
  }
  squareClick(i) {
    if (calculateWinner(this.state.squares) || this.state.squares[i])
      return;
    const squares = this.state.squares.slice();
    squares[i] = this.state.isXTurn ? 'X' : 'O';
    this.setState({
      squares: squares,
      isXTurn: !this.state.isXTurn,
    });
    if (calculateWinner(squares) === 'X') {
      this.setState({
        XWins: this.state.XWins + 1,
      })
    }
    if (calculateWinner(squares) === 'O') {
      this.setState({
        OWins: this.state.OWins + 1,
      })
    }
  }
  resetGame() {
    this.setState({
      squares: Array(9).fill(null),
      isXTurn: true,
    })
  }
  render() {
    return (
      <div id="game">
        X Wins: {this.state.XWins}<br />
        O Wins: {this.state.OWins}
        <Board
          squares={this.state.squares}
          onClick={i => this.squareClick(i)}
          isXTurn={this.state.isXTurn}
        />
        <button className="reset-button"
          onClick={() => this.resetGame()}>
        Reset
        </button>
      </div>
    );
  }
}

function calculateWinner(squares) {
  const lines = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [0, 4, 8],
    [2, 4, 6]
  ];
  for (let i = 0; i < lines.length; i++) {
    const [a, b, c] = lines[i];
    if (squares[a] && squares[a] === squares[b] && squares[a] === squares[c]) {
      return squares[a];
    }
  }
  return null;
}

export default Game;
